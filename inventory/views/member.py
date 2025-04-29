import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from decimal import Decimal

# 从新的模型结构导入
from ..models import Member, MemberLevel, RechargeRecord, OperationLog, Sale, MemberTransaction
from ..forms import MemberForm, MemberLevelForm, RechargeForm, MemberImportForm
from ..utils import validate_csv
from ..services import member_service

import csv
import io
import uuid
from datetime import datetime, timedelta


def member_search_by_phone(request, phone):
    """
    根据手机号搜索会员的API
    支持精确匹配和模糊匹配，返回多个匹配结果
    """
    try:
        # 先尝试精确匹配手机号
        member = Member.objects.get(phone=phone)
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'member_id': member.id,
            'member_name': member.name,
            'member_phone': member.phone,
            'member_level': member.level.name,
            'discount_rate': float(member.level.discount),
            'member_balance': float(member.balance),
            'member_points': member.points,
            'member_gender': member.get_gender_display(),
            'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            'member_total_spend': float(member.total_spend),
            'member_purchase_count': member.purchase_count
        })
    except Member.DoesNotExist:
        # 如果精确匹配失败，尝试模糊匹配手机号或姓名
        members = Member.objects.filter(
            models.Q(phone__icontains=phone) | 
            models.Q(name__icontains=phone)
        ).order_by('phone')[:5]  # 限制返回数量
        
        if members.exists():
            # 如果只有一个匹配结果
            if members.count() == 1:
                member = members.first()
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'member_id': member.id,
                    'member_name': member.name,
                    'member_phone': member.phone,
                    'member_level': member.level.name,
                    'discount_rate': float(member.level.discount),
                    'member_balance': float(member.balance),
                    'member_points': member.points,
                    'member_gender': member.get_gender_display(),
                    'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
                    'member_total_spend': float(member.total_spend),
                    'member_purchase_count': member.purchase_count
                })
            # 如果有多个匹配结果
            else:
                member_list = []
                for member in members:
                    member_list.append({
                        'member_id': member.id,
                        'member_name': member.name,
                        'member_phone': member.phone,
                        'member_level': member.level.name,
                        'discount_rate': float(member.level.discount),
                        'member_balance': float(member.balance),
                        'member_points': member.points
                    })
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'members': member_list
                })
        else:
            return JsonResponse({'success': False, 'message': '未找到会员'})


@login_required
def member_list(request):
    """会员列表视图"""
    # 获取筛选参数
    search_query = request.GET.get('search', '')
    level_id = request.GET.get('level', '')
    status = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')
    
    # 基本查询集
    members = Member.objects.select_related('level').all()
    
    # 应用筛选
    if search_query:
        members = members.filter(
            Q(name__icontains=search_query) | 
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(member_id__icontains=search_query)
        )
    
    if level_id:
        members = members.filter(level_id=level_id)
    
    if status == 'active':
        members = members.filter(is_active=True)
    elif status == 'inactive':
        members = members.filter(is_active=False)
    
    # 排序
    if sort_by == 'name':
        members = members.order_by('name')
    elif sort_by == 'points':
        members = members.order_by('-points')
    elif sort_by == 'level':
        members = members.order_by('level__priority', 'name')
    elif sort_by == 'created':
        members = members.order_by('-created_at')
    
    # 分页
    paginator = Paginator(members, 15)  # 每页15个会员
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 获取会员等级列表用于筛选
    levels = MemberLevel.objects.filter(is_active=True).order_by('priority')
    
    # 计算统计数据
    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()
    
    context = {
        'page_obj': page_obj,
        'levels': levels,
        'search_query': search_query,
        'selected_level': level_id,
        'selected_status': status,
        'sort_by': sort_by,
        'total_members': total_members,
        'active_members': active_members,
    }
    
    return render(request, 'inventory/member/member_list.html', context)


@login_required
def member_detail(request, pk):
    """会员详情视图"""
    member = get_object_or_404(Member, pk=pk)
    
    # 获取会员交易记录
    transactions = MemberTransaction.objects.filter(member=member).order_by('-created_at')[:20]
    
    # 获取会员购买记录
    sales = Sale.objects.filter(member=member).order_by('-created_at')[:20]
    
    # 计算统计数据
    total_spent = Sale.objects.filter(member=member).aggregate(total=Sum('total_amount'))['total'] or 0
    visit_count = Sale.objects.filter(member=member).count()
    
    # 最近30天的统计
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_spent = Sale.objects.filter(member=member, created_at__gte=thirty_days_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    recent_visit_count = Sale.objects.filter(member=member, created_at__gte=thirty_days_ago).count()
    
    context = {
        'member': member,
        'transactions': transactions,
        'sales': sales,
        'total_spent': total_spent,
        'visit_count': visit_count,
        'recent_spent': recent_spent,
        'recent_visit_count': recent_visit_count,
    }
    
    return render(request, 'inventory/member/member_detail.html', context)


@login_required
def member_create(request):
    """创建会员视图"""
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            # 保存会员数据
            member = form.save(commit=False)
            
            # 如果没有设置会员ID，生成一个
            if not member.member_id:
                current_date = datetime.now().strftime('%Y%m%d')
                random_suffix = str(uuid.uuid4().int)[:6]  # 使用UUID的前6位数字
                member.member_id = f'M{current_date}{random_suffix}'
            
            member.created_by = request.user
            member.save()
            
            messages.success(request, f'会员 {member.name} 创建成功')
            
            # 如果需要继续添加
            if 'save_and_add' in request.POST:
                return redirect('member_create')
            
            return redirect('member_detail', pk=member.id)
    else:
        form = MemberForm()
        
        # 生成默认会员ID
        current_date = datetime.now().strftime('%Y%m%d')
        random_suffix = str(uuid.uuid4().int)[:6]  # 使用UUID的前6位数字
        default_member_id = f'M{current_date}{random_suffix}'
        
        form.fields['member_id'].initial = default_member_id
        
        # 设置默认会员等级
        try:
            default_level = MemberLevel.objects.filter(is_active=True, is_default=True).first()
            if default_level:
                form.fields['level'].initial = default_level.id
        except:
            pass
    
    context = {
        'form': form,
        'title': '创建会员',
        'submit_text': '保存会员',
    }
    
    return render(request, 'inventory/member/member_form.html', context)


@login_required
def member_update(request, pk):
    """更新会员视图"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            # 保存会员数据
            member = form.save(commit=False)
            member.updated_at = timezone.now()
            member.updated_by = request.user
            member.save()
            
            messages.success(request, f'会员 {member.name} 更新成功')
            return redirect('member_detail', pk=member.id)
    else:
        form = MemberForm(instance=member)
    
    context = {
        'form': form,
        'member': member,
        'title': f'编辑会员: {member.name}',
        'submit_text': '更新会员',
    }
    
    return render(request, 'inventory/member/member_form.html', context)


@login_required
def member_delete(request, pk):
    """删除会员视图"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        member_name = member.name
        
        # 标记为不活跃而不是真的删除
        member.is_active = False
        member.updated_at = timezone.now()
        member.updated_by = request.user
        member.save()
        
        messages.success(request, f'会员 {member_name} 已标记为不活跃')
        return redirect('member_list')
    
    return render(request, 'inventory/member/member_confirm_delete.html', {
        'member': member
    })


@login_required
def member_level_list(request):
    """会员等级列表视图"""
    # 获取会员等级
    levels = MemberLevel.objects.all().order_by('priority')
    
    # 添加会员数量统计
    levels = levels.annotate(member_count=Count('member'))
    
    context = {
        'levels': levels,
    }
    
    return render(request, 'inventory/member/level_list.html', context)


@login_required
def member_level_create(request):
    """创建会员等级视图"""
    if request.method == 'POST':
        form = MemberLevelForm(request.POST)
        if form.is_valid():
            level = form.save()
            messages.success(request, f'会员等级 {level.name} 创建成功')
            return redirect('member_level_list')
    else:
        # 获取最大优先级
        max_priority = MemberLevel.objects.aggregate(max_priority=Count('priority'))['max_priority'] or 0
        
        form = MemberLevelForm(initial={'priority': max_priority + 1})
    
    context = {
        'form': form,
        'title': '创建会员等级',
        'submit_text': '保存等级',
    }
    
    return render(request, 'inventory/member/level_form.html', context)


@login_required
def member_level_update(request, pk):
    """更新会员等级视图"""
    level = get_object_or_404(MemberLevel, pk=pk)
    
    if request.method == 'POST':
        form = MemberLevelForm(request.POST, instance=level)
        if form.is_valid():
            level = form.save()
            messages.success(request, f'会员等级 {level.name} 更新成功')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm(instance=level)
    
    context = {
        'form': form,
        'level': level,
        'title': f'编辑会员等级: {level.name}',
        'submit_text': '更新等级',
    }
    
    return render(request, 'inventory/member/level_form.html', context)


@login_required
def member_level_delete(request, pk):
    """删除会员等级视图"""
    level = get_object_or_404(MemberLevel, pk=pk)
    
    # 检查是否有会员使用此等级
    member_count = Member.objects.filter(level=level).count()
    
    # 检查是否为默认等级
    is_default = level.is_default
    
    if request.method == 'POST':
        if member_count > 0 and not request.POST.get('force_delete'):
            messages.error(request, f'等级 {level.name} 下有 {member_count} 个会员，无法删除')
            return redirect('member_level_list')
        
        if is_default and not request.POST.get('force_delete'):
            messages.error(request, f'等级 {level.name} 是默认等级，无法删除')
            return redirect('member_level_list')
        
        level_name = level.name
        
        # 如果强制删除，将会员移到默认等级
        if member_count > 0:
            default_level = None
            if not level.is_default:
                default_level = MemberLevel.objects.filter(is_default=True).first()
            
            if not default_level:
                default_level = MemberLevel.objects.exclude(id=level.id).first()
                
            if default_level:
                Member.objects.filter(level=level).update(level=default_level)
        
        # 删除等级
        level.delete()
        
        messages.success(request, f'会员等级 {level_name} 已删除')
        return redirect('member_level_list')
    
    context = {
        'level': level,
        'member_count': member_count,
        'is_default': is_default,
    }
    
    return render(request, 'inventory/member/level_confirm_delete.html', context)


@login_required
def member_import(request):
    """导入会员视图"""
    if request.method == 'POST':
        form = MemberImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # 验证CSV文件
            validation_result = validate_csv(csv_file, 
                                            required_headers=['name', 'phone'],
                                            expected_headers=['name', 'phone', 'email', 
                                                            'member_id', 'level', 'points',
                                                            'birthday', 'address'])
            
            if not validation_result['valid']:
                messages.error(request, f"CSV文件验证失败: {validation_result['errors']}")
                return render(request, 'inventory/member/member_import.html', {'form': form})
            
            # 处理CSV文件
            try:
                result = member_service.import_members_from_csv(csv_file, request.user)
                
                messages.success(request, f"成功导入 {result['success']} 个会员. {result['skipped']} 个被跳过, {result['failed']} 个失败.")
                
                if result['failed_rows']:
                    error_messages = []
                    for row_num, error in result['failed_rows']:
                        error_messages.append(f"行 {row_num}: {error}")
                    
                    # 将错误消息限制在合理范围内
                    if len(error_messages) > 5:
                        error_messages = error_messages[:5] + [f"... 及其他 {len(error_messages) - 5} 个错误."]
                    
                    for error in error_messages:
                        messages.warning(request, error)
                
                return redirect('member_list')
            
            except Exception as e:
                messages.error(request, f"导入过程中发生错误: {str(e)}")
                return render(request, 'inventory/member/member_import.html', {'form': form})
    else:
        form = MemberImportForm()
    
    # 生成样例CSV数据
    sample_data = [
        ['name', 'phone', 'email', 'member_id', 'level', 'points', 'birthday', 'address'],
        ['张三', '13800138000', 'zhangsan@example.com', 'M202401001', '普通会员', '100', '1990-01-01', '北京市朝阳区'],
        ['李四', '13900139000', 'lisi@example.com', 'M202401002', '金卡会员', '500', '1985-05-05', '上海市浦东新区'],
    ]
    
    # 创建内存中的CSV
    sample_csv = io.StringIO()
    writer = csv.writer(sample_csv)
    for row in sample_data:
        writer.writerow(row)
    
    sample_csv_content = sample_csv.getvalue()
    
    context = {
        'form': form,
        'sample_csv': sample_csv_content,
    }
    
    return render(request, 'inventory/member/member_import.html', context)


@login_required
def member_export(request):
    """导出会员视图"""
    # 获取筛选参数
    level_id = request.GET.get('level', '')
    status = request.GET.get('status', '')
    
    # 基本查询集
    members = Member.objects.select_related('level').all()
    
    # 应用筛选
    if level_id:
        members = members.filter(level_id=level_id)
    
    if status == 'active':
        members = members.filter(is_active=True)
    elif status == 'inactive':
        members = members.filter(is_active=False)
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="members_export.csv"'
    
    # 写入CSV
    writer = csv.writer(response)
    writer.writerow(['ID', '会员号', '姓名', '手机', '邮箱', '会员等级', '积分', '生日', '地址', '备注', '状态'])
    
    for member in members:
        writer.writerow([
            member.id,
            member.member_id,
            member.name,
            member.phone,
            member.email or '',
            member.level.name if member.level else '',
            member.points,
            member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            member.address or '',
            member.notes or '',
            '启用' if member.is_active else '禁用',
        ])
    
    return response


@login_required
def member_points_adjust(request, pk):
    """调整会员积分视图"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        points_change = request.POST.get('points_change')
        description = request.POST.get('description', '')
        
        try:
            points_change = int(points_change)
            
            # 创建积分交易记录
            transaction = MemberTransaction.objects.create(
                member=member,
                transaction_type='POINTS_ADJUST',
                points_change=points_change,
                description=description,
                created_by=request.user
            )
            
            # 更新会员积分
            member.points += points_change
            member.save()
            
            # 检查是否需要升级会员等级
            member_service.check_and_update_member_level(member)
            
            messages.success(request, f'会员积分已调整: {points_change:+d}')
            return redirect('member_detail', pk=member.id)
            
        except ValueError:
            messages.error(request, '积分必须是整数')
    
    return render(request, 'inventory/member/points_adjust.html', {
        'member': member
    })


@login_required
def member_recharge(request, pk):
    """会员充值视图"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        actual_amount = Decimal(request.POST.get('actual_amount', '0'))
        payment_method = request.POST.get('payment_method', 'cash')
        remark = request.POST.get('remark', '')
        
        if amount <= 0:
            messages.error(request, '充值金额必须大于0')
            return redirect('member_recharge', pk=pk)
        
        # 创建充值记录
        recharge = RechargeRecord.objects.create(
            member=member,
            amount=amount,
            actual_amount=actual_amount,
            payment_method=payment_method,
            operator=request.user,
            remark=remark
        )
        
        # 创建余额交易记录
        transaction = MemberTransaction.objects.create(
            member=member,
            transaction_type='RECHARGE',
            balance_change=amount,
            points_change=0,  # 充值暂不增加积分
            description=f'会员充值 - {dict(RechargeRecord.PAYMENT_CHOICES).get(payment_method, "未知")}',
            remark=remark,
            created_by=request.user
        )
        
        # 更新会员余额和状态
        member.balance += amount
        member.is_recharged = True
        member.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='MEMBER',
            details=f'为会员 {member.name} 充值 {amount} 元',
            related_object_id=recharge.id,
            related_content_type=ContentType.objects.get_for_model(RechargeRecord)
        )
        
        messages.success(request, f'已成功为 {member.name} 充值 {amount} 元')
        return redirect('member_detail', pk=member.pk)
    
    return render(request, 'inventory/member/member_recharge.html', {
        'member': member
    })


@login_required
def member_recharge_records(request, pk):
    """会员充值记录视图"""
    member = get_object_or_404(Member, pk=pk)
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')
    
    return render(request, 'inventory/member/member_recharge_records.html', {
        'member': member,
        'recharge_records': recharge_records
    })


@login_required
def member_balance_adjust(request, pk):
    """调整会员余额视图"""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        balance_change = request.POST.get('balance_change')
        description = request.POST.get('description', '')
        
        try:
            balance_change = Decimal(balance_change)
            
            # 创建余额交易记录
            transaction = MemberTransaction.objects.create(
                member=member,
                transaction_type='BALANCE_ADJUST',
                balance_change=balance_change,
                description=description,
                created_by=request.user
            )
            
            # 更新会员余额
            member.balance += balance_change
            member.save()
            
            messages.success(request, f'会员余额已调整: {balance_change:+.2f}')
            return redirect('member_detail', pk=member.id)
            
        except ValueError:
            messages.error(request, '余额必须是有效的金额')
    
    return render(request, 'inventory/member/balance_adjust.html', {
        'member': member
    })


# 添加别名函数以兼容旧的导入
def member_edit(request, pk):
    """
    member_update的别名函数，用于保持向后兼容性
    """
    return member_update(request, pk)


# 添加更多别名函数和缺失的功能
def member_details(request, pk):
    """
    member_detail的别名函数，用于保持向后兼容性
    """
    return member_detail(request, pk)

def member_level_edit(request, pk):
    """
    member_level_update的别名函数，用于保持向后兼容性
    """
    return member_level_update(request, pk)

@login_required
def member_add_ajax(request):
    """
    通过AJAX添加会员的视图函数
    用于在销售过程中快速添加会员
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        
        # 基本验证
        if not name or not phone:
            return JsonResponse({'success': False, 'message': '姓名和手机号必须填写'})
        
        # 验证手机号是否已存在
        if Member.objects.filter(phone=phone).exists():
            return JsonResponse({'success': False, 'message': f'手机号{phone}已被使用'})
        
        try:
            # 生成会员ID
            current_date = datetime.now().strftime('%Y%m%d')
            random_suffix = str(uuid.uuid4().int)[:6]
            member_id = f'M{current_date}{random_suffix}'
            
            # 获取默认会员等级
            default_level = MemberLevel.objects.filter(is_active=True, is_default=True).first()
            if not default_level:
                default_level = MemberLevel.objects.filter(is_active=True).first()
            
            # 创建会员
            member = Member.objects.create(
                name=name,
                phone=phone,
                email=email,
                member_id=member_id,
                level=default_level,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'member_id': member.id,
                'member_name': member.name,
                'member_phone': member.phone,
                'member_level': member.level.name if member.level else '',
                'member_balance': float(member.balance),
                'member_points': member.points
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'创建会员失败: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': '只支持POST请求'}) 