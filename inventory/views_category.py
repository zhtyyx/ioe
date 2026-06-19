from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

# 使用重构后的模型导入
from inventory.models import Category, OperationLog
from inventory.forms import CategoryForm

@login_required
def category_list(request):
    """商品分类列表视图"""
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    """创建商品分类视图"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'添加商品分类: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(category)
            )
            
            messages.success(request, '商品分类添加成功')
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'inventory/category_form.html', {'form': form})

@login_required
def category_edit(request, category_id):
    """编辑商品分类视图"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'编辑商品分类: {category.name}',
                related_object_id=category.id,
                related_content_type=ContentType.objects.get_for_model(category)
            )
            
            messages.success(request, '商品分类更新成功')
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


# ===== 颜色管理 =====

@login_required
def color_list(request):
    """颜色列表视图"""
    from inventory.models import Color
    colors = Color.objects.all().order_by('name')
    return render(request, 'inventory/color_list.html', {'colors': colors})


@login_required
def color_create(request):
    """创建颜色视图"""
    from inventory.models import Color
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name:
            if not Color.objects.filter(name=name).exists():
                Color.objects.create(name=name, code=code)
                messages.success(request, f'颜色 "{name}" 添加成功')
            else:
                messages.error(request, f'颜色 "{name}" 已存在')
        else:
            messages.error(request, '颜色名称不能为空')
        return redirect('color_list')
    return render(request, 'inventory/color_form.html')


@login_required
def color_edit(request, color_id):
    """编辑颜色视图"""
    from inventory.models import Color
    color = get_object_or_404(Color, id=color_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name:
            if Color.objects.filter(name=name).exclude(id=color_id).exists():
                messages.error(request, f'颜色 "{name}" 已存在')
            else:
                color.name = name
                color.code = code
                color.save()
                messages.success(request, f'颜色 "{name}" 更新成功')
        else:
            messages.error(request, '颜色名称不能为空')
        return redirect('color_list')
    return render(request, 'inventory/color_form.html', {'color': color})


@login_required
def color_delete(request, color_id):
    """删除颜色视图"""
    from inventory.models import Color
    color = get_object_or_404(Color, id=color_id)
    if request.method == 'POST':
        color_name = color.name
        color.delete()
        messages.success(request, f'颜色 "{color_name}" 已删除')
        return redirect('color_list')
    return render(request, 'inventory/color_confirm_delete.html', {'color': color})


# ===== 尺码管理 =====

@login_required
def size_list(request):
    """尺码列表视图"""
    from inventory.models import Size
    sizes = Size.objects.all().order_by('name')
    return render(request, 'inventory/size_list.html', {'sizes': sizes})


@login_required
def size_create(request):
    """创建尺码视图"""
    from inventory.models import Size
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            if not Size.objects.filter(name=name).exists():
                Size.objects.create(name=name)
                messages.success(request, f'尺码 "{name}" 添加成功')
            else:
                messages.error(request, f'尺码 "{name}" 已存在')
        else:
            messages.error(request, '尺码名称不能为空')
        return redirect('size_list')
    return render(request, 'inventory/size_form.html')


@login_required
def size_edit(request, size_id):
    """编辑尺码视图"""
    from inventory.models import Size
    size = get_object_or_404(Size, id=size_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            if Size.objects.filter(name=name).exclude(id=size_id).exists():
                messages.error(request, f'尺码 "{name}" 已存在')
            else:
                size.name = name
                size.save()
                messages.success(request, f'尺码 "{name}" 更新成功')
        else:
            messages.error(request, '尺码名称不能为空')
        return redirect('size_list')
    return render(request, 'inventory/size_form.html', {'size': size})


@login_required
def size_delete(request, size_id):
    """删除尺码视图"""
    from inventory.models import Size
    size = get_object_or_404(Size, id=size_id)
    if request.method == 'POST':
        size_name = size.name
        size.delete()
        messages.success(request, f'尺码 "{size_name}" 已删除')
        return redirect('size_list')
    return render(request, 'inventory/size_confirm_delete.html', {'size': size})