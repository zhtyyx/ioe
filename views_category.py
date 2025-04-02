from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from .models import Category, OperationLog
from .forms import CategoryForm

@login_required
def category_list(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='OTHER',
                details=f'创建商品分类: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(Category)
            )
            
            messages.success(request, '分类添加成功')
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'inventory/category_form.html', {'form': form})

@login_required
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='OTHER',
                details=f'编辑商品分类: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(Category)
            )
            
            messages.success(request, '分类更新成功')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'inventory/category_form.html', {'form': form, 'category': category})

@login_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    # 检查该分类是否有关联的商品
    if category.product_set.exists():
        messages.error(request, f'无法删除分类 "{category.name}"，因为有商品关联到此分类')
        return redirect('category_list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='OTHER',
            details=f'删除商品分类: {category_name}',
            related_object_id=0,  # 已删除，无ID
            related_content_type=ContentType.objects.get_for_model(Category)
        )
        
        messages.success(request, f'分类 "{category_name}" 已成功删除')
        return redirect('category_list')
    
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})