/**
 * 增强型表单验证和用户体验脚本
 * 用于优化移动端适配、表单验证、批量操作和安全机制
 */

document.addEventListener('DOMContentLoaded', function() {
    // 增强表单验证
    enhanceFormValidation();
    
    // 优化移动端表格和表单布局
    enhanceMobileResponsiveness();
    
    // 添加批量操作功能
    setupBatchOperations();
    
    // 增强密码策略和二次确认机制
    enhanceSecurityFeatures();
});

/**
 * 增强表单验证功能
 */
function enhanceFormValidation() {
    // 获取所有需要验证的表单
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // 为所有表单添加验证类
        form.classList.add('needs-validation');
        
        // 为必填字段添加视觉提示
        form.querySelectorAll('[required]').forEach(field => {
            // 获取字段的标签
            const label = form.querySelector(`label[for="${field.id}"]`);
            if (label && !label.querySelector('.required-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'required-indicator text-danger ms-1';
                indicator.textContent = '*';
                label.appendChild(indicator);
            }
            
            // 添加实时验证反馈
            field.addEventListener('input', function() {
                validateField(this);
            });
            
            field.addEventListener('blur', function() {
                validateField(this, true);
            });
        });
        
        // 表单提交前验证
        form.addEventListener('submit', function(event) {
            let isValid = true;
            
            // 验证所有必填字段
            form.querySelectorAll('[required]').forEach(field => {
                if (!validateField(field, true)) {
                    isValid = false;
                }
            });
            
            // 验证密码字段
            const passwordField = form.querySelector('input[type="password"]');
            if (passwordField && passwordField.value && !validatePassword(passwordField.value)) {
                isValid = false;
                showValidationError(passwordField, '密码必须包含至少8个字符，包括大小写字母、数字和特殊字符');
            }
            
            // 如果验证失败，阻止表单提交
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
                
                // 滚动到第一个错误字段
                const firstInvalidField = form.querySelector('.is-invalid');
                if (firstInvalidField) {
                    firstInvalidField.focus();
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });
}

/**
 * 验证单个字段
 * @param {HTMLElement} field - 要验证的表单字段
 * @param {boolean} showError - 是否显示错误信息
 * @returns {boolean} - 验证是否通过
 */
function validateField(field, showError = false) {
    let isValid = field.checkValidity();
    
    // 特殊字段验证
    if (field.type === 'email' && field.value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        isValid = emailRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, '请输入有效的电子邮件地址');
        }
    } else if (field.type === 'tel' && field.value) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        isValid = phoneRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, '请输入有效的手机号码');
        }
    } else if (field.name === 'barcode' && field.value) {
        // 条码验证逻辑
        const barcodeRegex = /^[A-Za-z0-9\-]{4,}$/;
        isValid = barcodeRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, '条码格式不正确，请检查');
        }
    }
    
    // 显示或隐藏验证反馈
    if (showError) {
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            
            // 移除现有的错误消息
            const errorElement = field.nextElementSibling;
            if (errorElement && errorElement.classList.contains('invalid-feedback')) {
                errorElement.remove();
            }
        } else if (!field.classList.contains('is-invalid')) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            
            // 如果没有自定义错误消息，添加默认消息
            if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('invalid-feedback')) {
                showValidationError(field, '此字段是必填的');
            }
        }
    }
    
    return isValid;
}

/**
 * 显示验证错误信息
 * @param {HTMLElement} field - 表单字段
 * @param {string} message - 错误信息
 */
function showValidationError(field, message) {
    // 移除现有的错误消息
    const existingError = field.nextElementSibling;
    if (existingError && existingError.classList.contains('invalid-feedback')) {
        existingError.remove();
    }
    
    // 创建新的错误消息
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    // 插入错误消息
    field.parentNode.insertBefore(errorDiv, field.nextSibling);
}

/**
 * 验证密码强度
 * @param {string} password - 密码
 * @returns {boolean} - 密码是否符合要求
 */
function validatePassword(password) {
    // 密码必须至少8个字符，包含大小写字母、数字和特殊字符
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/;
    return passwordRegex.test(password);
}

/**
 * 优化移动端表格和表单布局
 */
function enhanceMobileResponsiveness() {
    // 优化表格在移动设备上的显示
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        // 为表格添加水平滚动提示
        const tableContainer = table.closest('.table-responsive');
        if (tableContainer && !tableContainer.querySelector('.swipe-hint')) {
            const hint = document.createElement('div');
            hint.className = 'swipe-hint d-md-none text-muted small mb-2';
            hint.innerHTML = '<i class="bi bi-arrow-left-right me-1"></i>左右滑动查看更多';
            tableContainer.insertBefore(hint, table);
        }
        
        // 为表格行添加触摸反馈
        table.querySelectorAll('tbody tr').forEach(row => {
            row.addEventListener('touchstart', function() {
                this.classList.add('active-touch');
            }, { passive: true });
            
            row.addEventListener('touchend', function() {
                this.classList.remove('active-touch');
            }, { passive: true });
        });
    });
    
    // 优化表单在移动设备上的布局
    const formGroups = document.querySelectorAll('.form-group, .mb-3');
    formGroups.forEach(group => {
        // 确保标签和输入框在小屏幕上垂直堆叠
        const label = group.querySelector('label');
        const input = group.querySelector('input, select, textarea');
        
        if (label && input) {
            label.classList.add('d-block');
            input.classList.add('w-100');
        }
    });
    
    // 优化下拉选择框在移动端的显示
    document.querySelectorAll('select').forEach(select => {
        select.addEventListener('focus', function() {
            if (window.innerWidth < 768) {
                // 在移动设备上，确保下拉框不会被截断
                this.style.maxHeight = '38px';
            }
        });
    });
}

/**
 * 设置批量操作功能
 */
function setupBatchOperations() {
    // 添加批量选择功能
    setupBatchSelection();
    
    // 添加批量操作按钮
    setupBatchActionButtons();
}

/**
 * 设置批量选择功能
 */
function setupBatchSelection() {
    // 查找所有表格
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        // 检查表格是否已经有选择列
        const hasCheckboxColumn = table.querySelector('thead th.select-column');
        if (!hasCheckboxColumn) {
            // 添加表头选择列
            const headerRow = table.querySelector('thead tr');
            if (headerRow) {
                const selectAllHeader = document.createElement('th');
                selectAllHeader.className = 'select-column';
                selectAllHeader.style.width = '40px';
                
                const selectAllCheckbox = document.createElement('input');
                selectAllCheckbox.type = 'checkbox';
                selectAllCheckbox.className = 'form-check-input select-all';
                selectAllCheckbox.setAttribute('aria-label', '选择所有行');
                
                selectAllHeader.appendChild(selectAllCheckbox);
                headerRow.insertBefore(selectAllHeader, headerRow.firstChild);
                
                // 为每一行添加选择框
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const selectCell = document.createElement('td');
                    selectCell.className = 'select-column';
                    
                    const rowCheckbox = document.createElement('input');
                    rowCheckbox.type = 'checkbox';
                    rowCheckbox.className = 'form-check-input select-row';
                    rowCheckbox.setAttribute('aria-label', '选择此行');
                    
                    selectCell.appendChild(rowCheckbox);
                    row.insertBefore(selectCell, row.firstChild);
                });
                
                // 添加全选/取消全选功能
                selectAllCheckbox.addEventListener('change', function() {
                    const isChecked = this.checked;
                    table.querySelectorAll('.select-row').forEach(checkbox => {
                        checkbox.checked = isChecked;
                    });
                    
                    // 更新批量操作按钮状态
                    updateBatchActionButtons();
                });
                
                // 添加行选择事件
                table.querySelectorAll('.select-row').forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        updateBatchActionButtons();
                        
                        // 更新全选框状态
                        const allCheckboxes = table.querySelectorAll('.select-row');
                        const checkedCheckboxes = table.querySelectorAll('.select-row:checked');
                        selectAllCheckbox.checked = allCheckboxes.length === checkedCheckboxes.length;
                        selectAllCheckbox.indeterminate = checkedCheckboxes.length > 0 && checkedCheckboxes.length < allCheckboxes.length;
                    });
                });
            }
        }
    });
}

/**
 * 设置批量操作按钮
 */
function setupBatchActionButtons() {
    // 查找可以添加批量操作按钮的容器
    const actionContainers = document.querySelectorAll('.card-body .d-flex.flex-wrap.gap-2');
    
    actionContainers.forEach(container => {
        // 检查是否已经有批量操作按钮组
        if (!container.querySelector('.batch-actions')) {
            // 创建批量操作按钮组
            const batchActionsDiv = document.createElement('div');
            batchActionsDiv.className = 'batch-actions dropdown d-none ms-2';
            
            // 创建下拉菜单按钮
            const dropdownButton = document.createElement('button');
            dropdownButton.className = 'btn btn-outline-primary dropdown-toggle';
            dropdownButton.type = 'button';
            dropdownButton.setAttribute('data-bs-toggle', 'dropdown');
            dropdownButton.setAttribute('aria-expanded', 'false');
            dropdownButton.innerHTML = '<i class="bi bi-list-check me-1"></i> 批量操作 <span class="badge bg-primary ms-1 selected-count">0</span>';
            
            // 创建下拉菜单
            const dropdownMenu = document.createElement('ul');
            dropdownMenu.className = 'dropdown-menu';
            
            // 添加批量操作选项
            const actions = [
                { text: '批量导出', icon: 'bi-download', action: 'exportSelected' },
                { text: '批量删除', icon: 'bi-trash', action: 'deleteSelected', class: 'text-danger' }
            ];
            
            // 根据页面类型添加特定操作
            if (window.location.pathname.includes('/product/')) {
                actions.splice(1, 0, { text: '批量调整价格', icon: 'bi-currency-yen', action: 'adjustPrice' });
            } else if (window.location.pathname.includes('/inventory/')) {
                actions.splice(1, 0, { text: '批量调整库存', icon: 'bi-box-seam', action: 'adjustStock' });
            }
            
            // 创建菜单项
            actions.forEach(action => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.className = `dropdown-item batch-action ${action.class || ''}`;
                a.href = '#';
                a.setAttribute('data-action', action.action);
                a.innerHTML = `<i class="bi ${action.icon} me-2"></i>${action.text}`;
                
                li.appendChild(a);
                dropdownMenu.appendChild(li);
                
                // 添加事件监听器
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    handleBatchAction(this.getAttribute('data-action'));
                });
            });
            
            // 组装下拉菜单
            batchActionsDiv.appendChild(dropdownButton);
            batchActionsDiv.appendChild(dropdownMenu);
            
            // 添加到容器
            container.appendChild(batchActionsDiv);
        }
    });
    
    // 初始化批量操作按钮状态
    updateBatchActionButtons();
}

/**
 * 更新批量操作按钮状态
 */
function updateBatchActionButtons() {
    const selectedRows = document.querySelectorAll('.select-row:checked');
    const batchActions = document.querySelectorAll('.batch-actions');
    
    batchActions.forEach(actionDiv => {
        if (selectedRows.length > 0) {
            actionDiv.classList.remove('d-none');
            actionDiv.querySelector('.selected-count').textContent = selectedRows.length;
        } else {
            actionDiv.classList.add('d-none');
        }
    });
}

/**
 * 处理批量操作
 * @param {string} action - 操作类型
 */
function handleBatchAction(action) {
    // 获取选中的行
    const selectedRows = document.querySelectorAll('.select-row:checked');
    const selectedIds = Array.from(selectedRows).map(checkbox => {
        const row = checkbox.closest('tr');
        return row.getAttribute('data-id') || '';
    }).filter(id => id);
    
    if (selectedIds.length === 0) {
        showAlert('请先选择要操作的项目', 'warning');
        return;
    }
    
    switch (action) {
        case 'exportSelected':
            exportSelectedItems(selectedIds);
            break;
        case 'deleteSelected':
            confirmDeleteSelected(selectedIds);
            break;
        case 'adjustPrice':
            showAdjustPriceModal(selectedIds);
            break;
        case 'adjustStock':
            showAdjustStockModal(selectedIds);
            break;
        default:
            console.warn('未知的批量操作:', action);
    }
}

/**
 * 导出选中项目
 * @param {Array} ids - 选中项目的ID
 */
function exportSelectedItems(ids) {
    // 创建一个表单来提交导出请求
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'export/';
    form.style.display = 'none';
    
    // 添加CSRF令牌
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // 添加选中的ID
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // 提交表单
    document.body.appendChild(form);
    form.submit();
}

/**
 * 确认删除选中项目
 * @param {Array} ids - 选中项目的ID
 */
function confirmDeleteSelected(ids) {
    Swal.fire({
        title: '确认删除',
        text: `您确定要删除选中的 ${ids.length} 项吗？此操作不可逆！`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        focusCancel: true
    }).then((result) => {
        if (result.isConfirmed) {
            // 执行删除操作
            deleteSelectedItems(ids);
        }
    });
}

/**
 * 删除选中项目
 * @param {Array} ids - 选中项目的ID
 */
function deleteSelectedItems(ids) {
    // 创建一个表单来提交删除请求
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-delete/';
    form.style.display = 'none';
    
    // 添加CSRF令牌
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // 添加选中的ID
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // 提交表单
    document.body.appendChild(form);
    form.submit();
}

/**
 * 显示调整价格模态框
 * @param {Array} ids - 选中项目的ID
 */
function showAdjustPriceModal(ids) {
    // 创建模态框HTML
    const modalHtml = `
    <div class="modal fade" id="adjustPriceModal" tabindex="-1" aria-labelledby="adjustPriceModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustPriceModalLabel">批量调整价格</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustPriceForm">
                        <div class="mb-3">
                            <label for="adjustmentType" class="form-label">调整方式</label>
                            <select class="form-select" id="adjustmentType" required>
                                <option value="percentage">按百分比调整</option>
                                <option value="fixed">按固定金额调整</option>
                                <option value="set">设置为指定金额</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="adjustmentValue" class="form-label">调整值</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="adjustmentValue" step="0.01" required>
                                <span class="input-group-text adjustment-unit">%</span>
                            </div>
                            <div class="form-text">正值表示增加，负值表示减少</div>
                        </div>
                        <div class="mb-3">
                            <label for="adjustField" class="form-label">调整字段</label>
                            <select class="form-select" id="adjustField" required>
                                <option value="price">售价</option>
                                <option value="cost">成本价</option>
                                <option value="both">售价和成本价</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" id="confirmAdjustPrice">确认调整</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // 添加模态框到页面
    if (!document.getElementById('adjustPriceModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // 获取模态框元素
    const modal = document.getElementById('adjustPriceModal');
    const bsModal = new bootstrap.Modal(modal);
    
    // 更新调整单位显示
    const adjustmentType = document.getElementById('adjustmentType');
    const adjustmentUnit = document.querySelector('.adjustment-unit');
    
    adjustmentType.addEventListener('change', function() {
        adjustmentUnit.textContent = this.value === 'percentage' ? '%' : '¥';
    });
    
    // 确认按钮点击事件
    document.getElementById('confirmAdjustPrice').addEventListener('click', function() {
        const form = document.getElementById('adjustPriceForm');
        if (form.checkValidity()) {
            const type = document.getElementById('adjustmentType').value;
            const value = document.getElementById('adjustmentValue').value;
            const field = document.getElementById('adjustField').value;
            
            // 提交调整请求
            submitPriceAdjustment(ids, type, value, field);
            bsModal.hide();
        } else {
            form.classList.add('was-validated');
        }
    });
    
    // 显示模态框
    bsModal.show();
}

/**
 * 提交价格调整请求
 * @param {Array} ids - 选中项目的ID
 * @param {string} type - 调整类型
 * @param {number} value - 调整值
 * @param {string} field - 调整字段
 */
function submitPriceAdjustment(ids, type, value, field) {
    // 创建一个表单来提交调整请求
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-adjust-price/';
    form.style.display = 'none';
    
    // 添加CSRF令牌
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // 添加调整参数
    const typeInput = document.createElement('input');
    typeInput.type = 'hidden';
    typeInput.name = 'adjustment_type';
    typeInput.value = type;
    form.appendChild(typeInput);
    
    const valueInput = document.createElement('input');
    valueInput.type = 'hidden';
    valueInput.name = 'adjustment_value';
    valueInput.value = value;
    form.appendChild(valueInput);
    
    const fieldInput = document.createElement('input');
    fieldInput.type = 'hidden';
    fieldInput.name = 'adjustment_field';
    fieldInput.value = field;
    form.appendChild(fieldInput);
    
    // 添加选中的ID
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // 提交表单
    document.body.appendChild(form);
    form.submit();
}

/**
 * 显示调整库存模态框
 * @param {Array} ids - 选中项目的ID
 */
function showAdjustStockModal(ids) {
    // 创建模态框HTML
    const modalHtml = `
    <div class="modal fade" id="adjustStockModal" tabindex="-1" aria-labelledby="adjustStockModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustStockModalLabel">批量调整库存</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustStockForm">
                        <div class="mb-3">
                            <label for="stockAdjustmentType" class="form-label">调整方式</label>
                            <select class="form-select" id="stockAdjustmentType" required>
                                <option value="add">增加库存</option>
                                <option value="subtract">减少库存</option>
                                <option value="set">设置为指定数量</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentValue" class="form-label">调整数量</label>
                            <input type="number" class="form-control" id="stockAdjustmentValue" min="0" step="1" required>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentNotes" class="form-label">调整原因</label>
                            <textarea class="form-control" id="stockAdjustmentNotes" rows="3" required></textarea>
                        </div