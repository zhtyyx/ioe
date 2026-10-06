// Checkout cart, membership and payment interactions. Loaded only by sale_form.html.
document.addEventListener('DOMContentLoaded', function() {
    // 变量初始化
    const productSearchInput = document.getElementById('product-search-input');
    const productTableBody = document.getElementById('product-table-body');
    const memberIdInput = document.getElementById('member-id');
    const memberInfoBox = document.getElementById('member-info-box');
    const paymentButtons = document.querySelectorAll('.payment-btn');
    const paymentMethodInput = document.getElementById('payment-method');
    const memberSearchInput = document.getElementById('member-search-input');
    window.updateTotalsTimeout = null; // 用于节流 updateTotals

    // 商品搜索处理
    if (productSearchInput) {
        let lastInputTime = 0;
        let inputBuffer = '';

        productSearchInput.addEventListener('keypress', function(event) {
            const currentTime = new Date().getTime();

            if (currentTime - lastInputTime < 50) {
                inputBuffer += event.key;
            } else {
                inputBuffer = event.key;
            }

            lastInputTime = currentTime;

            if (event.key === 'Enter') {
                event.preventDefault();
                if (inputBuffer.length > 0) {
                    searchProductByBarcode(productSearchInput.value);
                    productSearchInput.value = '';
                    inputBuffer = '';
                }
            }
        });
    }

    // 会员搜索
    if (memberSearchInput) {
        memberSearchInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const query = this.value.trim();
                if (query.length > 0) {
                    searchMember(query);
                }
            }
        });
    }

    // 支付方式选择
    if (paymentButtons) {
        paymentButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                // 移除其他按钮的选中状态
                paymentButtons.forEach(b => b.classList.remove('active'));
                // 添加当前按钮的选中状态
                this.classList.add('active');
                // 更新隐藏输入字段
                const paymentMethod = this.getAttribute('data-payment');
                if (paymentMethodInput) {
                    paymentMethodInput.value = paymentMethod;
                }
            });
        });
    }

    // 根据条码搜索商品
    window.searchProductByBarcode = function(barcode) {
        if (!barcode || barcode.trim() === '') {
            showAlert('warning', '请输入商品条码或名称');
            return;
        }

        fetch(`/api/product/search/barcode/${barcode}/`)
            .then(response => {
                if (!response.ok) {
                    console.error(`[API Error] Network response was not ok for barcode ${barcode}:`, response.status, response.statusText);
                    throw new Error('网络请求失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    if (data.multiple_matches && data.products && Array.isArray(data.products) && data.products.length > 0) {
                        // **确保传递给模态框的数据结构统一**
                        const standardizedProducts = data.products.map(p => ({
                            id: p.product_id || p.id, // 适配两种可能的 key
                            name: p.name,
                            price: parseFloat(p.price) || 0,
                            stock: parseInt(p.stock) || 0,
                            spec: p.specification || p.spec || '' // 适配多种可能的 key
                        }));
                        showProductSelectionModal(standardizedProducts);
                    } else if (data.product_id || (data.product && data.product.id)) {
                        // **处理单结果，强制统一结构**
                        const productSource = data.product || data; // API 可能直接返回顶级字段
                        const productData = {
                            id: productSource.product_id || productSource.id,
                            name: productSource.name,
                            price: parseFloat(productSource.price) || 0,
                            stock: parseInt(productSource.stock) || 0,
                            spec: productSource.specification || productSource.spec || ''
                        };
                         // **再次校验构建的对象**
                        if (!productData.id || !productData.name) {
                            console.error("[API Error] Failed to standardize single product data:", productData, "Original data:", data);
                            showAlert('error', '获取商品信息格式错误');
                        } else {
                            addProductToList(productData);
                        }
                    } else {
                        // 即使 success 为 true，也可能没有有效商品数据
                        console.warn(`[API Warning] Barcode search success=true but no valid single product data for ${barcode}. Response:`, data);
                        showAlert('warning', data.message || '未找到匹配的商品信息');
                         // 尝试名称搜索作为后备
                         searchProductByName(barcode);
                    }
                } else {
                    // 条码搜索失败，尝试名称搜索
                    searchProductByName(barcode);
                }
            })
            .catch(error => {
                console.error('条码搜索商品错误:', error);
                showAlert('error', '通过条码查询商品时出错');
                // 即使出错，也尝试名称搜索作为后备
                searchProductByName(barcode);
            });
    }

    // 通过名称搜索商品
    window.searchProductByName = function(name) {
        // 使用正确的API端点搜索商品
        fetch(`/api/product/search/?query=${encodeURIComponent(name)}`)
            .then(response => {
                if (!response.ok) {
                     console.error(`[API Error] Network response was not ok for name ${name}:`, response.status, response.statusText);
                    throw new Error('网络请求失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.products && Array.isArray(data.products) && data.products.length > 0) {
                    // **确保传递给模态框的数据结构统一**
                    const standardizedProducts = data.products.map(p => ({
                        id: p.id, // 名称搜索 API 返回的是 id
                        name: p.name,
                        price: parseFloat(p.price) || 0,
                        stock: parseInt(p.stock) || 0,
                        spec: p.specification || p.spec || ''
                    }));
                    showProductSelectionModal(standardizedProducts);
                } else {
                    console.warn(`[API Warning] Name search did not find valid products for ${name}. Response:`, data);
                    showAlert('warning', data.message || '未找到匹配的商品');
                }
            })
            .catch(error => {
                console.error('名称搜索商品错误:', error);
                showAlert('error', '通过名称查询商品时出错');
            });
    }

    // 会员搜索
    window.searchMember = function(query) {
        if (!query || query.trim() === '') {
            showAlert('warning', '请输入会员手机号或姓名');
            return;
        }

        fetch(`/api/member/search/${query}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络请求失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    if (data.multiple_matches && data.members && data.members.length > 0) {
                        showMemberSelectionModal(data.members);
                    } else if (data.member_id) {
                        selectMember(data.member_id, data.member_name, data.discount_rate, data.member_phone);
                    }
                } else {
                    showAlert('info', data.message || '未找到会员');
                }
            })
            .catch(error => {
                console.error('搜索会员错误:', error);
                showAlert('error', '查询会员信息失败');
            });
    }

    // 选择会员
    window.selectMember = function(memberId, memberName, discountRate, phone) {
        // 设置会员ID
        if (memberIdInput) {
            memberIdInput.value = memberId;
        }

        // 显示会员信息
        document.getElementById('member-name-value').textContent = memberName || '未知';
        document.getElementById('member-phone-value').textContent = phone || '未知';

        // 计算并显示折扣
        const discountText = discountRate < 1 ? `${(discountRate * 10).toFixed(1)}折` : '无折扣';
        document.getElementById('member-discount-value').textContent = discountText;

        // 显示会员信息区域
        if (memberInfoBox) memberInfoBox.style.display = 'block';

        // 更新总计
        updateTotals();
        showAlert('success', '已选择会员');

        // 清空搜索框
        if (memberSearchInput) {
            memberSearchInput.value = '';
        }
    }

    // 编辑会员
    window.editMember = function() {
        const memberId = memberIdInput ? memberIdInput.value : '';
        if (!memberId) {
            showAlert('warning', '请先选择会员');
            return;
        }

        // 跳转到会员编辑页面
        window.open(`/members/${memberId}/edit/`, '_blank');
    }

    // 清除会员
    window.clearMember = function() {
        // 清除会员ID
        if (memberIdInput) {
            memberIdInput.value = '';
        }

        // 隐藏会员信息区域
        if (memberInfoBox) {
            memberInfoBox.style.display = 'none';
        }

        // 更新总计
        updateTotals();
        showAlert('info', '已清除会员信息');
    }

    // 商品选择模态框 (确保添加事件监听时使用标准化的数据)
    function showProductSelectionModal(products) {
        const modalBody = document.getElementById('product-selection-content');
        if (!modalBody) return;

        modalBody.innerHTML = '';

        products.forEach(product => {
            const productItem = document.createElement('div');
            productItem.className = 'card mb-2';
            // **使用标准化后的 product 对象的属性**
            productItem.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${product.name}</h5>
                    <p class="card-text">价格: ¥${product.price.toFixed(2)} | 库存: ${product.stock}</p>
                    <button class="btn btn-primary select-product-btn">
                        选择此商品
                    </button>
                </div>
            `;
            // **将标准化数据直接附加到按钮上**
            const selectButton = productItem.querySelector('.select-product-btn');
            if (selectButton) {
                // 移除旧的 data-* 属性方式，直接存储对象引用
                selectButton._productData = product;
                selectButton.addEventListener('click', function() {
                     // 直接使用存储的对象
                     addProductToList(this._productData);
                     // 关闭模态框
                     const modal = bootstrap.Modal.getInstance(document.getElementById('product-selection-modal'));
                     if (modal) modal.hide();
                });
            }
            modalBody.appendChild(productItem);
        });

        // 移除旧的选择器和事件绑定逻辑
        // document.querySelectorAll('.select-product-btn').forEach(btn => { ... });

        // 显示模态框
        const modalElement = document.getElementById('product-selection-modal');
        if (!modalElement) return;
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }

    // 会员选择模态框
    function showMemberSelectionModal(members) {
        const modalBody = document.getElementById('member-selection-content');
        if (!modalBody) return;

        modalBody.innerHTML = '';

        members.forEach(member => {
            const memberItem = document.createElement('div');
            memberItem.className = 'card mb-2';
            memberItem.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${member.member_name}</h5>
                    <p class="card-text">电话: ${member.member_phone}</p>
                    <button class="btn btn-primary select-member-btn"
                        data-id="${member.member_id}"
                        data-name="${member.member_name}"
                        data-phone="${member.member_phone}"
                        data-discount="${member.discount_rate || 1}">
                        选择此会员
                    </button>
                </div>
            `;
            modalBody.appendChild(memberItem);
        });

        // 添加选择事件
        document.querySelectorAll('.select-member-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const memberId = this.dataset.id;
                const memberName = this.dataset.name;
                const phone = this.dataset.phone;
                const discountRate = parseFloat(this.dataset.discount);

                selectMember(memberId, memberName, discountRate, phone);

                // 关闭模态框
                const modalElement = document.getElementById('member-selection-modal');
                if (modalElement) {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                         modal.hide();
                         // **在模态框隐藏后，将焦点移回会员搜索框**
                         modalElement.addEventListener('hidden.bs.modal', () => {
                              const memberSearchInputElement = document.getElementById('member-search-input');
                              if (memberSearchInputElement) {
                                   memberSearchInputElement.focus();
                              }
                         }, { once: true }); // 确保事件只触发一次
                    }
                }
            });
        });

        // 显示模态框
        const modalElementToShow = document.getElementById('member-selection-modal');
        if (!modalElementToShow) return;
        const modal = new bootstrap.Modal(modalElementToShow);
        modal.show();
    }

    // 将商品添加到列表
    window.addProductToList = function(product) {
        // **增加参数校验**
        if (!product || typeof product !== 'object' || !product.id) {
            console.error("[addProductToList] Invalid product data received:", product);
            showAlert('error', '无法添加商品：商品数据无效');
            return;
        }

        const productTableBody = document.getElementById('product-table-body'); // 在函数内部获取，确保最新
        if (!productTableBody) {
            console.error("[addProductToList] Error: productTableBody element not found!");
            showAlert('error', '发生内部错误：无法找到商品列表区域');
            return;
        }

        // 检查商品是否已存在
        const existingRow = productTableBody.querySelector(`tr[data-product-id="${product.id}"]`);
        if (existingRow) {
            // 增加数量
            const quantityInput = existingRow.querySelector('.quantity-input');
            if (quantityInput) {
                const currentQty = parseInt(quantityInput.value) || 0;
                const newQty = currentQty + 1;

                // 检查库存限制
                const maxStock = parseInt(existingRow.dataset.maxStock) || 0;
                if (maxStock > 0 && newQty > maxStock) {
                    showAlert('warning', `库存不足，当前库存: ${maxStock}`);
                    return;
                }

                quantityInput.value = newQty;

                // 更新小计和总计
                updateRowSubtotal(existingRow);
                updateTotals();
                showAlert('info', `商品 ${product.name} 数量已增加到 ${newQty}`);
            }
            return;
        }

        // --- 开始添加新行 ---
        const newRow = document.createElement('tr');
        newRow.dataset.productId = product.id;
        newRow.dataset.maxStock = product.stock;
        newRow.dataset.productName = product.name; // 添加额外数据属性
        const price = parseFloat(product.price) || 0; // 确保 price 已定义

        // **构建 row HTML**
        const rowHTML = `
            <td>${product.name}
                <input type="hidden" class="product-id-input" name="temp_product_id" value="${product.id}">
                <span class="d-none product-id-display">${product.id}</span>
            </td>
            <td>
                <div class="quantity-control">
                    <button type="button" class="btn btn-sm btn-outline-secondary decrease-btn">-</button>
                    <input type="number" class="form-control form-control-sm quantity-input" value="1" min="1" max="${product.stock || 9999}" style="width: 60px;">
                    <button type="button" class="btn btn-sm btn-outline-secondary increase-btn">+</button>
                </div>
            </td>
            <td>¥<input type="number" step="0.01" class="form-control form-control-sm price-input" value="${price.toFixed(2)}" style="width: 90px;"></td>
            <td>${product.spec || '无规格'}</td>
            <td class="text-end subtotal">¥${price.toFixed(2)}</td>
            <td class="text-center">
                <button type="button" class="btn btn-outline-danger btn-sm delete-btn">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        newRow.innerHTML = rowHTML;

        // **在追加前进行状态检查**
        if (productTableBody) {
        } else {
             console.error("[addProductToList] Before appendChild: productTableBody is null or undefined!");
             showAlert('error', '内部错误：无法定位商品列表。');
             return; // 如果 tbody 没了，就不能继续了
        }

        // **执行追加操作**
        try {
            productTableBody.appendChild(newRow);

            // **在追加后进行验证**
            const addedRowCheck = productTableBody.querySelector(`tr[data-product-id="${product.id}"]`);
            if (addedRowCheck && addedRowCheck.parentElement === productTableBody) {
            } else {
                 console.error(`[addProductToList] Verification FAILED: Row for product ${product.id} NOT found or not attached correctly after appendChild!`);
                 console.error(`[addProductToList] Checking last child:`, productTableBody.lastChild);
                 showAlert('error', `无法将商品 ${product.name} 正确添加到列表！请检查控制台。`);
                 // 考虑是否需要移除可能错误添加的行？ newRow.remove();
                 return; // 如果验证失败，停止后续操作
            }
        } catch (error) {
            console.error("[addProductToList] Error during appendChild:", error);
            showAlert('error', `添加商品时发生错误: ${error.message}`);
            return;
        }

        // --- 绑定事件 ---
        const decreaseBtn = newRow.querySelector('.decrease-btn');
        const increaseBtn = newRow.querySelector('.increase-btn');
        const quantityInput = newRow.querySelector('.quantity-input');
        const priceInput = newRow.querySelector('.price-input');
        const deleteBtn = newRow.querySelector('.delete-btn');

        // 减少数量
        if (decreaseBtn && quantityInput) {
            decreaseBtn.addEventListener('click', function() {
                let qty = parseInt(quantityInput.value) || 0;
                if (qty > 1) {
                    quantityInput.value = qty - 1;
                    updateRowSubtotal(newRow);
                    updateTotals();
                }
            });
        }

        // 增加数量
        if (increaseBtn && quantityInput) {
            increaseBtn.addEventListener('click', function() {
                let qty = parseInt(quantityInput.value) || 0;
                const maxStock = parseInt(newRow.dataset.maxStock) || 0;

                if (maxStock <= 0 || qty < maxStock) {
                    quantityInput.value = qty + 1;
                    updateRowSubtotal(newRow);
                    updateTotals();
                } else {
                    showAlert('warning', `库存不足，最大可用: ${maxStock}`);
                }
            });
        }

        // 数量变更 (使用 input 事件实时响应)
        if (quantityInput) {
            quantityInput.addEventListener('input', function() {
                let qty = parseInt(this.value) || 0;
                const maxStock = parseInt(newRow.dataset.maxStock) || 0;

                if (qty < 0) qty = 0; // 允许临时输入负数，但计算按0
                // 不在此处强制限制最大值，让用户输入，但在 updateRowSubtotal 中处理

                updateRowSubtotal(newRow); // 更新小计
                // 延迟更新总计，避免过于频繁的计算
                clearTimeout(window.updateTotalsTimeout);
                window.updateTotalsTimeout = setTimeout(updateTotals, 300);
            });
            // 保留 change 事件用于最终验证和格式化
            quantityInput.addEventListener('change', function() {
                 let qty = parseInt(this.value) || 0;
                 const maxStock = parseInt(newRow.dataset.maxStock) || 0;
                 if (qty < 1) {
                     this.value = 1;
                 } else if (maxStock > 0 && qty > maxStock) {
                     this.value = maxStock;
                     showAlert('warning', `库存不足，已设为最大可用: ${maxStock}`);
                 }
                 updateRowSubtotal(newRow); // 确保最终值被计算
                 updateTotals();
            });
        }

        // 价格变更 (使用 input 事件实时响应)
        if (priceInput) {
            priceInput.addEventListener('input', function() {
                let price = parseFloat(this.value) || 0;
                if (price < 0) price = 0;

                updateRowSubtotal(newRow); // 更新小计
                // 延迟更新总计
                clearTimeout(window.updateTotalsTimeout);
                window.updateTotalsTimeout = setTimeout(updateTotals, 300);
            });
             // 保留 change 事件用于最终验证和格式化
            priceInput.addEventListener('change', function() {
                 let price = parseFloat(this.value) || 0;
                 if (price < 0) {
                     this.value = '0.00';
                 } else {
                     this.value = price.toFixed(2); // 格式化
                 }
                 updateRowSubtotal(newRow); // 确保最终值被计算
                 updateTotals();
            });
        }

        // 删除行
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function() {
                const productName = product.name || '未知商品';
                newRow.remove();
                updateTotals();
                showAlert('info', `已移除商品: ${productName}`);
            });
        }

        // 更新总计
        updateTotals();
        showAlert('success', `已添加商品: ${product.name}`);
        if (productSearchInput) {
            requestAnimationFrame(() => productSearchInput.focus());
        }
    }

    // 更新行小计 (保持不变)
    function updateRowSubtotal(row) {
        const quantityInput = row.querySelector('.quantity-input');
        const priceInput = row.querySelector('.price-input');
        const subtotalCell = row.querySelector('.subtotal');

        if (!quantityInput || !priceInput || !subtotalCell) {
             console.error('Could not find elements for subtotal calculation in row:', row);
             return;
        }

        let quantity = parseInt(quantityInput.value) || 0;
        let price = parseFloat(priceInput.value) || 0;
        const maxStock = parseInt(row.dataset.maxStock) || 0;

        // 再次校验数量 (基于最终值)
        if (quantity < 1) quantity = 1;
        if (maxStock > 0 && quantity > maxStock) quantity = maxStock; // 按库存计算
        if (price < 0) price = 0;

        const subtotal = quantity * price;
        subtotalCell.textContent = `¥${subtotal.toFixed(2)}`;
    }

    // 更新总计 (增加健壮性)
    window.updateTotals = function() {
        let totalAmount = 0;
        const subtotalCells = productTableBody.querySelectorAll('tr[data-product-id] .subtotal'); // 更精确的选择器

        subtotalCells.forEach(cell => {
            const subtotal = parseFloat(cell.textContent.replace('¥', '')) || 0;
            totalAmount += subtotal;
        });

        // 更新商品总额
        const totalAmountElement = document.getElementById('total-amount');
        if (totalAmountElement) {
            totalAmountElement.textContent = totalAmount.toFixed(2);
        } else {
             console.error("Element '#total-amount' not found.");
        }

        // 计算折扣
        let discountRate = 1; // 默认无折扣
        let discountAmount = 0;
        const memberIdInputElement = document.getElementById('member-id');
        const memberId = memberIdInputElement ? memberIdInputElement.value : '';

        // 只有在有会员ID的情况下才考虑折扣
        if (memberId) {
            const discountTextElement = document.getElementById('member-discount-value');
            const discountText = discountTextElement ? discountTextElement.textContent : '';

            if (discountText && discountText !== '无折扣') {
                const match = discountText.match(/(\d+\.?\d*)折/);
                if (match && match[1]) {
                    discountRate = parseFloat(match[1]) / 10;
                    if (isNaN(discountRate) || discountRate < 0 || discountRate > 1) {
                        discountRate = 1; // 防御无效折扣率
                        console.warn("Invalid discount rate parsed:", match[1]);
                    }
                } else {
                    console.warn("Could not parse discount rate from:", discountText);
                }
        }
        }

        // 只有当折扣率<1时，才计算折扣金额
        if (discountRate < 1) {
            discountAmount = totalAmount * (1 - discountRate);
        } else {
            discountAmount = 0;
        }

        // 计算最终金额
        const finalAmount = totalAmount - discountAmount;

        // 更新折扣金额
        const discountAmountElement = document.getElementById('discount-amount');
        if (discountAmountElement) {
            discountAmountElement.textContent = discountAmount.toFixed(2);
        } else {
            console.error("Element '#discount-amount' not found.");
        }

        // 更新最终金额
        const finalAmountElement = document.getElementById('final-amount');
        if (finalAmountElement) {
            finalAmountElement.textContent = finalAmount.toFixed(2);
        } else {
            console.error("Element '#final-amount' not found.");
        }

        // 更新隐藏表单字段
        updateHiddenFields(totalAmount, discountAmount, finalAmount);
    }

    // 更新隐藏字段
    function updateHiddenFields(totalAmount, discountAmount, finalAmount) {
        const form = document.getElementById('sale-form');
        if (!form) return;

        function updateField(id, name, value) {
            let field = document.getElementById(id);
            if (!field) {
                field = document.createElement('input');
                field.type = 'hidden';
                field.id = id;
                field.name = name;
                form.appendChild(field);
            }
            field.value = value;
        }

        updateField('total-amount-input', 'total_amount', totalAmount.toFixed(2));
        updateField('discount-amount-input', 'discount_amount', discountAmount.toFixed(2));
        updateField('final-amount-input', 'final_amount', finalAmount.toFixed(2));
    }

    // 表单提交验证
    const saleForm = document.getElementById('sale-form');
    if (saleForm) {
        saleForm.addEventListener('submit', function(event) {
            // 先阻止默认提交，等验证完成后手动提交
            event.preventDefault();

            const currentProductTableBody = document.getElementById('product-table-body');
            if (!currentProductTableBody) {
                console.error("[Form Submit] CRITICAL ERROR: productTableBody element not found!");
                showAlert('error', '内部错误：无法验证购物车');
                return;
            }

            // 严格检查商品行
            const products = currentProductTableBody.querySelectorAll('tr[data-product-id]');

            // 没有商品时显示错误
            if (products.length === 0) {
                showAlert('error', '请至少添加一个商品');
                return;
            }

            // 支付方式检查
            const paymentMethodInput = document.getElementById('payment-method');
            const paymentMethod = paymentMethodInput ? paymentMethodInput.value : '';
            if (!paymentMethod) {
                showAlert('error', '请选择支付方式');
                return;
            }

            // 执行产品索引更新 - 创建隐藏字段
            updateProductIndices();

            // 检查表单数据是否包含商品
            const hasProductData = [...new FormData(saleForm).keys()].some(
                key => key.includes('products[') && key.includes('][id]')
            );

            if (!hasProductData) {
                console.error("[Form Submit] CRITICAL ERROR: No product data in form after updateProductIndices!");
                showAlert('error', '系统错误：表单数据准备失败，请联系管理员');

                return;
            }

            // 显示加载提示
            showAlert('info', '正在提交...');

            // 提交表单
            saleForm.submit();
        });
    }

    // **恢复 updateProductIndices 函数，并确保其逻辑正确**
    function updateProductIndices() {
       // 在函数内部重新获取 tbody，确保最新
       const currentTbody = document.getElementById('product-table-body');
       if (!currentTbody) {
            console.error("[updateProductIndices] Error: Cannot find product-table-body.");
            return;
       }
       const rows = currentTbody.querySelectorAll('tr[data-product-id]');

       // 先清除表单中已有的products字段，避免累积
       const form = document.getElementById('sale-form');
       if (form) {
           const existingInputs = form.querySelectorAll('input[name^="products["]');
           existingInputs.forEach(input => input.remove());
       }

       rows.forEach((row, index) => {
           if (!form) return;

           // 获取数据
           const productId = row.dataset.productId;
           const quantityInput = row.querySelector('input.quantity-input');
           const priceInput = row.querySelector('input.price-input');

           const quantity = quantityInput ? quantityInput.value : "1";
           const price = priceInput ? priceInput.value : "0.00";

           // 创建隐藏字段并直接添加到表单
           const idField = document.createElement('input');
           idField.type = 'hidden';
           idField.name = `products[${index}][id]`;
           idField.value = productId;
           form.appendChild(idField);

           const qtyField = document.createElement('input');
           qtyField.type = 'hidden';
           qtyField.name = `products[${index}][quantity]`;
           qtyField.value = quantity;
           form.appendChild(qtyField);

           const priceField = document.createElement('input');
           priceField.type = 'hidden';
           priceField.name = `products[${index}][price]`;
           priceField.value = price;
           form.appendChild(priceField);

       });

       // 更新商品数量计数和调试信息
       const productCountField = document.getElementById('product-count');
       if (productCountField) {
           productCountField.value = rows.length;
       }

       const debugInfoField = document.getElementById('debug-info');
       if (debugInfoField) {
           debugInfoField.value = JSON.stringify({
               timestamp: new Date().toISOString(),
               productCount: rows.length,
               productIds: Array.from(rows).map(row => row.dataset.productId)
           });
       }

    }

    // 快捷键支持
    document.addEventListener('keydown', function(event) {
        // F2 - 会员搜索
        if (event.key === 'F2') {
            event.preventDefault();
            if (memberSearchInput) {
                memberSearchInput.focus();
            }
        }

        // F3 - 商品搜索
        if (event.key === 'F3') {
            event.preventDefault();
            if (productSearchInput) {
                productSearchInput.focus();
            }
        }
    });

    // 消息提示
    window.showAlert = function(type, message) {
        const Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
        Toast.fire({
            icon: type,
            title: message
        });
    }

    // 初始化 - 聚焦商品搜索框
    if (productSearchInput) {
        productSearchInput.focus();
    }

    // 初始化时不再调用 updateProductIndices
    // updateProductIndices();
    updateTotals();
});
