/**
 * Main JavaScript file for Bank Optimization Web App
 */

// Global configuration
const CONFIG = {
    API_BASE_URL: '/api',
    POLLING_INTERVAL: 5000,
    MAX_FILE_SIZE: 16 * 1024 * 1024, // 16MB
    ALLOWED_EXTENSIONS: ['csv'],
    CHARTS: {},
    NOTIFICATIONS: {
        timeout: 5000,
        position: 'top-right'
    }
};

// Global state
const STATE = {
    currentResults: null,
    isOptimizing: false,
    uploadedFiles: {},
    kpiData: []
};

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Update current time in navbar
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validations
    initializeFormValidations();
    
    // Initialize notifications
    initializeNotifications();
    
    // Initialize page-specific functionality
    initializePageSpecific();
    
    console.log('Bank Optimization Web App initialized');
}

/**
 * Update current time display
 */
function updateCurrentTime() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        timeElement.textContent = now.toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize form validations
 */
function initializeFormValidations() {
    // File upload validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            validateFileInput(this);
        });
    });
    
    // Form submission validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                e.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
}

/**
 * Validate file input
 */
function validateFileInput(input) {
    const file = input.files[0];
    const feedback = input.parentNode.querySelector('.invalid-feedback') || 
                    createFeedbackElement(input);
    
    if (!file) {
        setInputInvalid(input, 'ファイルを選択してください');
        return false;
    }
    
    // Check file size
    if (file.size > CONFIG.MAX_FILE_SIZE) {
        setInputInvalid(input, `ファイルサイズが${CONFIG.MAX_FILE_SIZE / 1024 / 1024}MBを超えています`);
        return false;
    }
    
    // Check file extension
    const extension = file.name.split('.').pop().toLowerCase();
    if (!CONFIG.ALLOWED_EXTENSIONS.includes(extension)) {
        setInputInvalid(input, `${CONFIG.ALLOWED_EXTENSIONS.join(', ')}ファイルのみ対応しています`);
        return false;
    }
    
    setInputValid(input, 'ファイルが正常に選択されました');
    return true;
}

/**
 * Set input as invalid
 */
function setInputInvalid(input, message) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');
    
    const feedback = input.parentNode.querySelector('.invalid-feedback') ||
                    createFeedbackElement(input);
    feedback.textContent = message;
}

/**
 * Set input as valid
 */
function setInputValid(input, message = '') {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    
    if (message) {
        const feedback = input.parentNode.querySelector('.valid-feedback') ||
                        createFeedbackElement(input, 'valid');
        feedback.textContent = message;
    }
}

/**
 * Create feedback element
 */
function createFeedbackElement(input, type = 'invalid') {
    const feedback = document.createElement('div');
    feedback.className = `${type}-feedback`;
    input.parentNode.appendChild(feedback);
    return feedback;
}

/**
 * Validate entire form
 */
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            setInputInvalid(input, 'この項目は必須です');
            isValid = false;
        }
    });
    
    return isValid;
}

/**
 * Initialize notifications system
 */
function initializeNotifications() {
    // Create notifications container if it doesn't exist
    if (!document.getElementById('notifications-container')) {
        const container = document.createElement('div');
        container.id = 'notifications-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1060';
        document.body.appendChild(container);
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = CONFIG.NOTIFICATIONS.timeout) {
    const container = document.getElementById('notifications-container');
    const notification = document.createElement('div');
    const notificationId = 'notification-' + Date.now();
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-triangle',
        warning: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    const colors = {
        success: 'success',
        error: 'danger',
        warning: 'warning',
        info: 'info'
    };
    
    notification.innerHTML = `
        <div class="toast" id="${notificationId}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${colors[type]} text-white">
                <i class="fas ${icons[type]} me-2"></i>
                <strong class="me-auto">通知</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    container.appendChild(notification);
    
    const toast = new bootstrap.Toast(document.getElementById(notificationId), {
        delay: duration
    });
    
    toast.show();
    
    // Remove element after hide
    document.getElementById(notificationId).addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * Initialize page-specific functionality
 */
function initializePageSpecific() {
    const path = window.location.pathname;
    
    if (path.includes('/upload')) {
        initializeUploadPage();
    } else if (path.includes('/optimize')) {
        initializeOptimizePage();
    } else if (path.includes('/results')) {
        initializeResultsPage();
    } else if (path.includes('/kpi')) {
        initializeKPIPage();
    }
}

/**
 * Initialize upload page
 */
function initializeUploadPage() {
    console.log('Initializing upload page');
    
    // Drag and drop functionality
    initializeDragDrop();
    
    // File preview functionality
    initializeFilePreview();
}

/**
 * Initialize drag and drop
 */
function initializeDragDrop() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        const parent = input.parentNode;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            parent.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            parent.addEventListener(eventName, () => {
                parent.classList.add('drag-over');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            parent.addEventListener(eventName, () => {
                parent.classList.remove('drag-over');
            }, false);
        });
        
        parent.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                validateFileInput(input);
            }
        }, false);
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

/**
 * Initialize file preview
 */
function initializeFilePreview() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            showFilePreview(this);
        });
    });
}

/**
 * Show file preview
 */
function showFilePreview(input) {
    const file = input.files[0];
    if (!file) return;
    
    const previewContainer = input.parentNode.querySelector('.file-preview') ||
                           createFilePreviewContainer(input);
    
    previewContainer.innerHTML = `
        <div class="d-flex align-items-center mt-2 p-2 bg-light rounded">
            <i class="fas fa-file-csv text-success me-2"></i>
            <div class="flex-grow-1">
                <div class="fw-bold">${file.name}</div>
                <small class="text-muted">${formatFileSize(file.size)} • ${file.type || 'CSV'}</small>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="clearFileInput('${input.id}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
}

function createFilePreviewContainer(input) {
    const container = document.createElement('div');
    container.className = 'file-preview';
    input.parentNode.appendChild(container);
    return container;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function clearFileInput(inputId) {
    const input = document.getElementById(inputId);
    input.value = '';
    input.classList.remove('is-valid', 'is-invalid');
    
    const preview = input.parentNode.querySelector('.file-preview');
    if (preview) {
        preview.innerHTML = '';
    }
}

/**
 * Initialize optimize page
 */
function initializeOptimizePage() {
    console.log('Initializing optimize page');
    
    // Parameter sliders
    initializeParameterSliders();
    
    // Real-time parameter updates
    initializeParameterUpdates();
}

/**
 * Initialize parameter sliders
 */
function initializeParameterSliders() {
    const sliders = document.querySelectorAll('input[type="range"]');
    
    sliders.forEach(slider => {
        const valueDisplay = document.getElementById(slider.id + 'Value');
        
        slider.addEventListener('input', function() {
            if (valueDisplay) {
                let value = parseFloat(this.value);
                if (this.step === '0.01') {
                    value = value.toFixed(2);
                } else if (this.step === '0.1') {
                    value = value.toFixed(1);
                }
                valueDisplay.textContent = value;
            }
        });
        
        // Trigger initial update
        slider.dispatchEvent(new Event('input'));
    });
}

/**
 * Initialize parameter updates
 */
function initializeParameterUpdates() {
    const params = ['horizon', 'quantile', 'lambda_penalty', 'use_cutoff'];
    
    params.forEach(param => {
        const element = document.getElementById(param);
        if (element) {
            element.addEventListener('change', updateParameterPreview);
        }
    });
}

function updateParameterPreview() {
    // This could show a preview of how parameters affect the optimization
    console.log('Parameters updated');
}

/**
 * Initialize results page
 */
function initializeResultsPage() {
    console.log('Initializing results page');
    
    // Auto-refresh functionality
    initializeAutoRefresh();
    
    // Export functionality
    initializeExportFunctionality();
}

/**
 * Initialize auto-refresh
 */
function initializeAutoRefresh() {
    // Auto-refresh could be implemented here
    console.log('Auto-refresh initialized');
}

/**
 * Initialize export functionality
 */
function initializeExportFunctionality() {
    // Export functionality implementation
    console.log('Export functionality initialized');
}

/**
 * Initialize KPI page
 */
function initializeKPIPage() {
    console.log('Initializing KPI page');
    
    // Real-time KPI updates
    initializeKPIUpdates();
}

/**
 * Initialize KPI updates
 */
function initializeKPIUpdates() {
    // KPI real-time updates could be implemented here
    console.log('KPI updates initialized');
}

/**
 * Utility functions
 */

// Format number with commas
function formatNumber(num) {
    return num.toLocaleString('ja-JP');
}

// Format currency
function formatCurrency(amount) {
    return '¥' + formatNumber(amount);
}

// Format date
function formatDate(date) {
    return new Date(date).toLocaleString('ja-JP');
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// API helper functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showNotification('API呼び出しに失敗しました: ' + error.message, 'error');
        throw error;
    }
}

// Export utility functions for global use
window.BankOptimization = {
    showNotification,
    formatNumber,
    formatCurrency,
    formatDate,
    apiCall,
    clearFileInput
};