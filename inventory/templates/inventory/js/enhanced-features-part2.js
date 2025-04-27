/**
 * 显示库存调整模态框
 * @param {Array} ids - 选中项目的ID
 */
function showStockAdjustmentModal(ids) {
    // 创建模态框HTML
    const modalHtml = `
    <div class="modal fade" id="adjustStockModal" tabindex="-1" aria-labelledby="adjustStockModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustStockModalLabel">调整库存</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustStockForm" class="needs-validation" novalidate>
                        <div class="mb-3">
                            <label for="stockAdjustmentType" class="form-label">调整类型</label>
                            <select class="form-select" id="stockAdjustmentType" required>
                                <option value="">请选择调整类型</option>
                                <option value="add">增加库存</option>
                                <option value="subtract">减少库存</option>
                                <option value="set">设置库存</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentValue" class="form-label">调整数量</label>
                            <input type="number" class="form-control" id="stockAdjustmentValue" min="0" step="1" required>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentNotes" class="form-label">调整原因</label>
                            <textarea class="form-control" id="stockAdjustmentNotes" rows="3" required></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" id="confirmAdjustStock">确认调整</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // 添加模态框到页面
    if (!document.getElementById('adjustStockModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // 获取模态框元素
    const modal = document.getElementById('adjustStockModal');
    const bsModal = new bootstrap.Modal(modal);
    
    // 确认按钮点击事件
    document.getElementById('confirmAdjustStock').addEventListener('click', function() {
        const form = document.getElementById('adjustStockForm');
        if (form.checkValidity()) {
            const type = document.getElementById('stockAdjustmentType').value;
            const value = document.getElementById('stockAdjustmentValue').value;
            const notes = document.getElementById('stockAdjustmentNotes').value;
            
            // 提交调整请求
            submitStockAdjustment(ids, type, value, notes);
            bsModal.hide();
        } else {
            form.classList.add('was-validated');
        }
    });
    
    // 显示模态框
    bsModal.show();
}

/**
 * 提交库存调整请求
 * @param {Array} ids - 选中项目的ID
 * @param {string} type - 调整类型
 * @param {number} value - 调整值
 * @param {string} notes - 调整原因
 */
function submitStockAdjustment(ids, type, value, notes) {
    // 创建一个表单来提交调整请求
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-adjust-stock/';
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
    
    const notesInput = document.createElement('input');
    notesInput.type = 'hidden';
    notesInput.name = 'adjustment_notes';
    notesInput.value = notes;
    form.appendChild(notesInput);
    
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
 * 显示提示信息
 * @param {string} message - 提示信息
 * @param {string} type - 提示类型
 */
function showAlert(message, type = 'info') {
    Swal.fire({
        text: message,
        icon: type,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
    });
}

/**
 * 增强密码策略和二次确认机制
 */
function enhanceSecurityFeatures() {
    // 增强密码输入字段
    enhancePasswordFields();
    
    // 添加敏感操作二次确认
    addConfirmationForSensitiveActions();
}

/**
 * 增强密码输入字段
 */
function enhancePasswordFields() {
    // 获取所有密码输入字段
    const passwordFields = document.querySelectorAll('input[type="password"]');
    
    passwordFields.forEach(field => {
        // 创建密码强度指示器容器
        const strengthContainer = document.createElement('div');
        strengthContainer.className = 'password-strength-meter mt-2 d-none';
        
        // 创建密码强度进度条
        const strengthBar = document.createElement('div');
        strengthBar.className = 'progress';
        strengthBar.style.height = '5px';
        
        const strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'progress-bar';
        strengthIndicator.style.width = '0%';
        strengthIndicator.setAttribute('role', 'progressbar');
        strengthIndicator.setAttribute('aria-valuenow', '0');
        strengthIndicator.setAttribute('aria-valuemin', '0');
        strengthIndicator.setAttribute('aria-valuemax', '100');
        
        strengthBar.appendChild(strengthIndicator);
        
        // 创建密码强度文本
        const strengthText = document.createElement('small');
        strengthText.className = 'text-muted';
        
        // 添加到容器
        strengthContainer.appendChild(strengthBar);
        strengthContainer.appendChild(strengthText);
        
        // 添加到密码字段后面
        field.parentNode.insertBefore(strengthContainer, field.nextSibling);
        
        // 添加密码可见性切换按钮
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'btn btn-outline-secondary password-toggle';
        toggleButton.innerHTML = '<i class="bi bi-eye"></i>';
        toggleButton.setAttribute('aria-label', '显示密码');
        
        // 将密码字段包装在输入组中
        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group';
        
        // 重新排列元素
        field.parentNode.insertBefore(inputGroup, field);
        inputGroup.appendChild(field);
        inputGroup.appendChild(toggleButton);
        
        // 添加密码可见性切换功能
        toggleButton.addEventListener('click', function() {
            const type = field.getAttribute('type') === 'password' ? 'text' : 'password';
            field.setAttribute('type', type);
            this.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
            this.setAttribute('aria-label', type === 'password' ? '显示密码' : '隐藏密码');
        });
        
        // 添加密码强度检查
        field.addEventListener('input', function() {
            if (this.value) {
                strengthContainer.classList.remove('d-none');
                const strength = checkPasswordStrength(this.value);
                updatePasswordStrengthIndicator(strengthIndicator, strengthText, strength);
            } else {
                strengthContainer.classList.add('d-none');
            }
        });
        
        // 添加密码规则提示
        if (!field.getAttribute('aria-describedby')) {
            const passwordHelpId = `password-help-${Math.random().toString(36).substr(2, 9)}`;
            field.setAttribute('aria-describedby', passwordHelpId);
            
            const passwordHelp = document.createElement('div');
            passwordHelp.id = passwordHelpId;
            passwordHelp.className = 'form-text';
            passwordHelp.innerHTML = '密码必须至少包含8个字符，包括大小写字母、数字和特殊字符';
            
            field.parentNode.parentNode.appendChild(passwordHelp);
        }
    });
}