"""
系统日志管理相关视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.admin.models import LogEntry
from django.db.models import Q
from django.utils.html import escape
from django.http import FileResponse
from django.utils import timezone
import os
import logging
import re
from datetime import datetime, timedelta

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access

logger = logging.getLogger(__name__)

@login_required
@permission_required('is_superuser')
@log_view_access('OTHER')
def log_list(request):
    """系统日志列表视图"""
    # 获取查询参数
    search_query = request.GET.get('q', '')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # 构建过滤条件
    query = LogEntry.objects.all()
    
    if search_query:
        query = query.filter(
            Q(object_repr__icontains=search_query) | 
            Q(change_message__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    if action_type:
        query = query.filter(action_flag=int(action_type))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(action_time__gte=date_from_obj)
        except ValueError:
            messages.error(request, "开始日期格式无效")
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # 添加一天，使其包含结束日期的全天
            date_to_obj = date_to_obj + timedelta(days=1)
            query = query.filter(action_time__lt=date_to_obj)
        except ValueError:
            messages.error(request, "结束日期格式无效")
    
    # 分页
    page_size = int(request.GET.get('page_size', 50))
    paginator = Paginator(query.order_by('-action_time'), page_size)
    page_number = request.GET.get('page', 1)
    logs = paginator.get_page(page_number)
    
    # 准备统计数据
    stats = {
        'total': LogEntry.objects.count(),
        'add': LogEntry.objects.filter(action_flag=1).count(),
        'change': LogEntry.objects.filter(action_flag=2).count(),
        'delete': LogEntry.objects.filter(action_flag=3).count(),
    }
    
    # 准备文件日志数据
    log_files = []
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    
    if os.path.exists(log_dir):
        for file_name in os.listdir(log_dir):
            if file_name.endswith('.log'):
                file_path = os.path.join(log_dir, file_name)
                try:
                    size = os.path.getsize(file_path)
                    modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # 将字节转换为人类可读的格式
                    if size < 1024:
                        size_str = f"{size} bytes"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.2f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.2f} MB"
                    
                    log_files.append({
                        'name': file_name,
                        'path': file_path,
                        'size': size_str,
                        'modified': modified,
                    })
                except OSError:
                    continue
                    
        # 按修改时间排序
        log_files.sort(key=lambda x: x['modified'], reverse=True)
    
    context = {
        'logs': logs,
        'stats': stats,
        'log_files': log_files,
        'search_query': search_query,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'page_size': page_size,
    }
    
    return render(request, 'inventory/system/log_list.html', context)

@login_required
@permission_required('is_superuser')
@log_view_access('OTHER')
def clear_logs(request):
    """清除系统日志视图"""
    # 默认日期为30天前
    default_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        log_type = request.POST.get('log_type', '')
        date_before = request.POST.get('date_before', '')
        confirm = request.POST.get('confirm') == 'on'
        
        if not confirm:
            messages.error(request, "请确认您要清除日志")
            return redirect('log_list')
        
        try:
            # 根据日期过滤
            if date_before:
                try:
                    date_before_obj = datetime.strptime(date_before, '%Y-%m-%d')
                    date_before_obj = date_before_obj.replace(tzinfo=timezone.get_current_timezone())
                    query = LogEntry.objects.filter(action_time__lt=date_before_obj)
                except ValueError:
                    messages.error(request, "日期格式无效")
                    return redirect('log_list')
            else:
                query = LogEntry.objects.all()
            
            # 根据类型过滤
            if log_type and log_type.isdigit():
                query = query.filter(action_flag=int(log_type))
            
            # 获取要删除的记录数量
            count = query.count()
            
            # 删除日志
            query.delete()
            
            # 记录操作到日志
            logger.info(f"用户 {request.user.username} 清除了系统日志：类型 {log_type}，日期 {date_before} 之前，共 {count} 条记录")
            
            messages.success(request, f"成功清除 {count} 条日志记录")
            
        except Exception as e:
            messages.error(request, f"清除日志失败: {str(e)}")
            logger.error(f"清除日志失败: {str(e)}")
        
        return redirect('log_list')
    
    context = {
        'default_date': default_date
    }
    
    return render(request, 'inventory/system/clear_logs.html', context)

@login_required
@permission_required('is_superuser')
def view_log_file(request, file_name):
    """查看日志文件内容"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # 安全检查，确保文件名是一个有效的日志文件名
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "无效的日志文件名")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"日志文件 {file_name} 不存在")
        return redirect('log_list')
    
    # 获取行数限制
    lines = request.GET.get('lines', 500)
    try:
        lines = int(lines)
    except ValueError:
        lines = 500
    
    # 获取文件内容（尾部的指定行数）
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # 读取所有行并反转
            all_lines = f.readlines()
            total_lines = len(all_lines)
            
            # 获取最后的 lines 行
            if lines >= total_lines:
                content = ''.join(all_lines)
            else:
                content = ''.join(all_lines[-lines:])
            
            # 转换内容为安全HTML
            content = escape(content)
            
            return render(request, 'inventory/system/view_log_file.html', {
                'file_name': file_name,
                'content': content,
                'lines': lines,
                'total_lines': total_lines,
            })
            
    except Exception as e:
        messages.error(request, f"读取日志文件失败: {str(e)}")
        logger.error(f"读取日志文件失败: {str(e)}")
        return redirect('log_list')

@login_required
@permission_required('is_superuser')
def download_log_file(request, file_name):
    """下载日志文件"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # 安全检查，确保文件名是一个有效的日志文件名
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "无效的日志文件名")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"日志文件 {file_name} 不存在")
        return redirect('log_list')
    
    try:
        # 记录下载操作
        LogEntry.objects.create(
            user=request.user,
            action_flag=1,
            content_type_id=0,
            object_id=file_name,
            object_repr=f'下载日志: {file_name}',
            change_message=f'下载了日志文件 {file_name}'
        )
        
        # 返回文件响应
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
        return response
        
    except Exception as e:
        messages.error(request, f"下载日志文件失败: {str(e)}")
        logger.error(f"下载日志文件失败: {str(e)}")
        return redirect('log_list')

@login_required
@permission_required('is_superuser')
def delete_log_file(request, file_name):
    """删除日志文件"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    file_path = os.path.join(log_dir, file_name)
    
    # 安全检查，确保文件名是一个有效的日志文件名
    if not re.match(r'^[\w.-]+\.log$', file_name) or '..' in file_name:
        messages.error(request, "无效的日志文件名")
        return redirect('log_list')
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        messages.error(request, f"日志文件 {file_name} 不存在")
        return redirect('log_list')
    
    if request.method == 'POST':
        # 确认删除
        confirm = request.POST.get('confirm') == 'on'
        if not confirm:
            messages.error(request, "请确认您要删除此日志文件")
            return render(request, 'inventory/system/delete_log_file.html', {'file_name': file_name})
        
        try:
            # 删除文件
            os.remove(file_path)
            
            # 记录删除操作
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,
                content_type_id=0,
                object_id=file_name,
                object_repr=f'删除日志: {file_name}',
                change_message=f'删除了日志文件 {file_name}'
            )
            
            messages.success(request, f"成功删除日志文件 {file_name}")
            return redirect('log_list')
            
        except Exception as e:
            messages.error(request, f"删除日志文件失败: {str(e)}")
            logger.error(f"删除日志文件失败: {str(e)}")
            return redirect('log_list')
    
    return render(request, 'inventory/system/delete_log_file.html', {'file_name': file_name}) 