"""
Inventory check services.
"""
import datetime
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Count, Sum

from inventory.models import (
    Product,
    Inventory,
    InventoryCheck,
    InventoryCheckItem,
)
from inventory.exceptions import InventoryValidationError
from inventory.utils.logging import log_exception, log_action

class InventoryCheckService:
    """Service for inventory checking operations."""
    
    @staticmethod
    @log_exception
    def create_inventory_check(name, description, user, category=None):
        """
        Create a new inventory check.
        
        Args:
            name: The name of the inventory check
            description: Description of the check
            user: The user creating the check
            category: Optional category filter for the check
            
        Returns:
            InventoryCheck: The created inventory check
        """
        with transaction.atomic():
            # Create the inventory check
            inventory_check = InventoryCheck.objects.create(
                name=name,
                description=description,
                status='draft',
                created_by=user
            )
            
            # Query for products to include
            products_query = Product.objects.all()
            if category:
                products_query = products_query.filter(category=category)
            
            # Add inventory check items
            items = []
            for product in products_query:
                try:
                    inventory = Inventory.objects.get(product=product)
                    items.append(
                        InventoryCheckItem(
                            inventory_check=inventory_check,
                            product=product,
                            system_quantity=inventory.quantity
                        )
                    )
                except Inventory.DoesNotExist:
                    # Create inventory if it doesn't exist
                    inventory = Inventory.objects.create(
                        product=product,
                        quantity=0
                    )
                    items.append(
                        InventoryCheckItem(
                            inventory_check=inventory_check,
                            product=product,
                            system_quantity=0
                        )
                    )
            
            # Bulk create items
            if items:
                InventoryCheckItem.objects.bulk_create(items)
            
            # Log the action
            log_action(
                user=user,
                operation_type='INVENTORY_CHECK',
                details=f"创建库存盘点: {name}",
                related_object=inventory_check
            )
            
            return inventory_check
    
    @staticmethod
    @log_exception
    def start_inventory_check(inventory_check, user):
        """
        Start an inventory check.
        
        Args:
            inventory_check: The inventory check to start
            user: The user starting the check
            
        Returns:
            InventoryCheck: The updated inventory check
        """
        if inventory_check.status != 'draft':
            raise InventoryValidationError("只有草稿状态的盘点单可以开始盘点")
        
        inventory_check.status = 'in_progress'
        inventory_check.save(update_fields=['status'])
        
        # Log the action
        log_action(
            user=user,
            operation_type='INVENTORY_CHECK',
            details=f"开始库存盘点: {inventory_check.name}",
            related_object=inventory_check
        )
        
        return inventory_check
    
    @staticmethod
    @log_exception
    @transaction.atomic
    def record_check_item(inventory_check_item, actual_quantity, user, notes=""):
        """
        Record the actual quantity for an inventory check item.
        
        Args:
            inventory_check_item: The item to update
            actual_quantity: The actual quantity counted
            user: The user recording the check
            notes: Optional notes about the check
            
        Returns:
            InventoryCheckItem: The updated inventory check item
        """
        if inventory_check_item.inventory_check.status != 'in_progress':
            raise InventoryValidationError("只有进行中的盘点单可以记录盘点结果")
        
        if actual_quantity < 0:
            raise InventoryValidationError("实际数量不能为负数")
        
        inventory_check_item.actual_quantity = actual_quantity
        inventory_check_item.notes = notes
        inventory_check_item.checked_by = user
        inventory_check_item.checked_at = timezone.now()
        inventory_check_item.save()
        
        # Log the action
        log_action(
            user=user,
            operation_type='INVENTORY_CHECK',
            details=f"记录盘点项: {inventory_check_item.product.name}, 实际数量: {actual_quantity}",
            related_object=inventory_check_item
        )
        
        return inventory_check_item
    
    @staticmethod
    @log_exception
    @transaction.atomic
    def complete_inventory_check(inventory_check, user):
        """
        Complete an inventory check.
        
        Args:
            inventory_check: The inventory check to complete
            user: The user completing the check
            
        Returns:
            InventoryCheck: The updated inventory check
        """
        if inventory_check.status != 'in_progress' and inventory_check.status != 'approved':
            raise InventoryValidationError("只有进行中或已审核的盘点单可以标记为完成")
        
        # 如果是从进行中状态转换为完成，需要检查所有项目是否已盘点
        if inventory_check.status == 'in_progress':
            # Check if all items have been checked
            unchecked_items = inventory_check.items.filter(actual_quantity__isnull=True).count()
            if unchecked_items > 0:
                raise InventoryValidationError(f"还有 {unchecked_items} 个商品未盘点完成")
        
        inventory_check.status = 'completed'
        inventory_check.completed_at = timezone.now()
        inventory_check.save(update_fields=['status', 'completed_at'])
        
        # Log the action
        log_action(
            user=user,
            operation_type='INVENTORY_CHECK',
            details=f"完成库存盘点: {inventory_check.name}",
            related_object=inventory_check
        )
        
        return inventory_check
    
    @staticmethod
    @log_exception
    @transaction.atomic
    def approve_inventory_check(inventory_check, user, adjust_inventory=False):
        """
        Approve an inventory check and optionally adjust inventory.
        
        Args:
            inventory_check: The inventory check to approve
            user: The user approving the check
            adjust_inventory: Whether to adjust inventory quantities to match actual counts
            
        Returns:
            InventoryCheck: The updated inventory check
        """
        if inventory_check.status != 'completed':
            raise InventoryValidationError("只有已完成的盘点单可以审核")
        
        from inventory.services.inventory_service import InventoryService
        
        # If adjusting inventory, update quantities
        if adjust_inventory:
            for item in inventory_check.items.filter(difference__isnull=False):
                if item.difference != 0:  # Only adjust if there's a difference
                    try:
                        inventory = Inventory.objects.get(product=item.product)
                        
                        # Use the inventory service to update the stock
                        InventoryService.update_stock(
                            product=item.product,
                            quantity=item.actual_quantity,  # Set to actual quantity
                            transaction_type='ADJUST',
                            operator=user,
                            notes=f"库存盘点调整: {inventory_check.name}"
                        )
                    except Inventory.DoesNotExist:
                        # This shouldn't happen, but just in case
                        pass
        
        inventory_check.status = 'approved'
        inventory_check.approved_by = user
        inventory_check.approved_at = timezone.now()
        inventory_check.save(update_fields=['status', 'approved_by', 'approved_at'])
        
        # Log the action
        log_action(
            user=user,
            operation_type='INVENTORY_CHECK',
            details=f"审核库存盘点: {inventory_check.name}" + (", 并调整库存" if adjust_inventory else ""),
            related_object=inventory_check
        )
        
        return inventory_check
    
    @staticmethod
    @log_exception
    def cancel_inventory_check(inventory_check, user):
        """
        Cancel an inventory check.
        
        Args:
            inventory_check: The inventory check to cancel
            user: The user cancelling the check
            
        Returns:
            InventoryCheck: The updated inventory check
        """
        if inventory_check.status in ('approved', 'cancelled'):
            raise InventoryValidationError("已审核或已取消的盘点单不能取消")
        
        inventory_check.status = 'cancelled'
        inventory_check.save(update_fields=['status'])
        
        # Log the action
        log_action(
            user=user,
            operation_type='INVENTORY_CHECK',
            details=f"取消库存盘点: {inventory_check.name}",
            related_object=inventory_check
        )
        
        return inventory_check
    
    @staticmethod
    @log_exception
    def get_inventory_check_summary(inventory_check):
        """
        Get a summary of the inventory check.
        
        Args:
            inventory_check: The inventory check to summarize
            
        Returns:
            dict: Summary information
        """
        items = inventory_check.items.all()
        
        # Count items
        total_items = items.count()
        checked_items = items.filter(actual_quantity__isnull=False).count()
        
        # Calculate discrepancies
        items_with_discrepancy = items.filter(difference__isnull=False).exclude(difference=0).count()
        
        # Calculate total value (cost * quantity)
        system_value = sum(item.system_quantity * item.product.cost for item in items)
        
        actual_value = sum(
            (item.actual_quantity or 0) * item.product.cost
            for item in items.filter(actual_quantity__isnull=False)
        )
        
        return {
            'total_items': total_items,
            'checked_items': checked_items,
            'pending_items': total_items - checked_items,
            'items_with_discrepancy': items_with_discrepancy,
            'system_value': system_value,
            'actual_value': actual_value,
            'value_difference': actual_value - system_value,
        } 