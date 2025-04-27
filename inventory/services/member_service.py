"""
会员服务模块 - 处理会员相关的业务逻辑
"""
import csv
import io
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from ..models import Member, MemberLevel, MemberTransaction


def check_and_update_member_level(member):
    """
    检查会员积分并根据积分更新会员等级
    如果会员积分达到更高等级的门槛，自动升级会员等级
    """
    # 获取会员当前等级
    current_level = member.level
    
    # 获取所有可能的更高等级
    higher_levels = MemberLevel.objects.filter(
        points_threshold__lte=member.points,
        is_active=True
    ).order_by('-points_threshold')
    
    if higher_levels.exists():
        highest_eligible_level = higher_levels.first()
        
        # 如果有更高的等级，并且不是当前等级，则升级
        if highest_eligible_level != current_level:
            old_level_name = current_level.name if current_level else "无等级"
            
            # 记录会员等级变更
            MemberTransaction.objects.create(
                member=member,
                transaction_type='LEVEL_CHANGE',
                points_change=0,
                balance_change=0,
                description=f'会员等级升级: {old_level_name} → {highest_eligible_level.name}',
                created_by=member.created_by  # 使用会员的创建者作为操作者
            )
            
            # 更新会员等级
            member.level = highest_eligible_level
            member.save(update_fields=['level', 'updated_at'])
            
            return True, old_level_name, highest_eligible_level.name
    
    return False, None, None


def import_members_from_csv(csv_file, operator):
    """
    从CSV文件导入会员数据
    
    Parameters:
    - csv_file: 上传的CSV文件
    - operator: 执行导入操作的用户
    
    Returns:
    - dict: 包含导入结果的字典
    """
    # 重置文件指针
    csv_file.seek(0)
    
    # 读取CSV文件
    csv_data = csv_file.read().decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    success_count = 0
    skipped_count = 0
    failed_count = 0
    failed_rows = []
    
    # 获取默认会员等级
    default_level = MemberLevel.objects.filter(is_default=True, is_active=True).first()
    if not default_level:
        default_level = MemberLevel.objects.filter(is_active=True).first()
    
    # 开始导入
    for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
        try:
            with transaction.atomic():
                # 检查必填字段
                if not row.get('name') or not row.get('phone'):
                    failed_rows.append((row_num, "姓名和手机号为必填字段"))
                    failed_count += 1
                    continue
                
                # 检查手机号是否已存在
                if Member.objects.filter(phone=row.get('phone')).exists():
                    skipped_count += 1
                    continue
                
                # 处理会员等级
                level = default_level
                if row.get('level'):
                    try:
                        level_obj = MemberLevel.objects.get(name=row.get('level'))
                        level = level_obj
                    except MemberLevel.DoesNotExist:
                        pass  # 使用默认等级
                
                # 处理生日
                birthday = None
                if row.get('birthday'):
                    try:
                        birthday = datetime.strptime(row.get('birthday'), '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                # 处理积分
                points = 0
                if row.get('points'):
                    try:
                        points = int(row.get('points'))
                    except ValueError:
                        points = 0
                
                # 创建会员
                member = Member.objects.create(
                    name=row.get('name'),
                    phone=row.get('phone'),
                    email=row.get('email', ''),
                    member_id=row.get('member_id', ''),
                    level=level,
                    points=points,
                    birthday=birthday,
                    address=row.get('address', ''),
                    created_by=operator
                )
                
                success_count += 1
                
        except Exception as e:
            failed_count += 1
            failed_rows.append((row_num, str(e)))
    
    return {
        'success': success_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'failed_rows': failed_rows
    }


def get_member_statistics():
    """
    获取会员统计信息
    
    Returns:
    - dict: 包含会员统计信息的字典
    """
    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()
    
    # 按等级统计会员数量
    level_stats = []
    for level in MemberLevel.objects.filter(is_active=True):
        level_count = Member.objects.filter(level=level).count()
        if level_count > 0:
            level_stats.append({
                'level_name': level.name,
                'level_color': level.color,
                'count': level_count,
                'percentage': round(level_count / total_members * 100 if total_members > 0 else 0, 2)
            })
    
    # 本月新增会员
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_members_this_month = Member.objects.filter(created_at__gte=current_month_start).count()
    
    return {
        'total_members': total_members,
        'active_members': active_members,
        'inactive_members': total_members - active_members,
        'level_stats': level_stats,
        'new_members_this_month': new_members_this_month,
    } 