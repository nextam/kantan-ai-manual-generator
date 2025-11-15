/**
 * File: image_editor_standalone.js
 * Purpose: Standalone image editor that can be called from media library
 * Main functionality: Modal-based image editing (rotate, crop, filters)
 * Dependencies: Media library integration
 */

class ImageEditorStandalone {
    constructor() {
        this.currentImage = null;
        this.currentRotation = 0;
        this.config = {};
        this.originalImageData = null;
        this.canvas = null;
        this.ctx = null;
    }

    /**
     * Open image editor modal
     * @param {Object} config - Configuration options
     * @param {string} config.imageUrl - URL of image to edit
     * @param {number} config.mediaId - Media ID (optional)
     * @param {Function} config.onSave - Callback when save is complete
     * @param {Function} config.onCancel - Callback when cancelled
     */
    open(config = {}) {
        this.config = {
            imageUrl: config.imageUrl || null,
            mediaId: config.mediaId || null,
            onSave: config.onSave || null,
            onCancel: config.onCancel || null
        };

        if (!this.config.imageUrl) {
            console.error('Image URL is required');
            return;
        }

        // Reset state
        this.currentRotation = 0;
        this.originalImageData = null;

        // Create modal if not exists
        this.createModal();

        // Load image
        this.loadImage(this.config.imageUrl);

        // Show modal
        const modal = document.getElementById('imageEditorModal');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Create image editor modal HTML
     */
    createModal() {
        // Check if modal already exists
        if (document.getElementById('imageEditorModal')) {
            return;
        }

        const modalHTML = `
            <div id="imageEditorModal" class="image-editor-modal">
                <div class="image-editor-content">
                    <div class="image-editor-header">
                        <h3>画像編集</h3>
                        <button class="image-editor-close" onclick="ImageEditorStandalone.instance.close()">
                            <span class="material-icons">close</span>
                        </button>
                    </div>

                    <div class="image-editor-toolbar">
                        <div class="toolbar-group">
                            <button class="toolbar-btn" onclick="ImageEditorStandalone.instance.rotate(-90)" title="左に90度回転">
                                <span class="material-icons">rotate_left</span>
                                <span>左回転</span>
                            </button>
                            <button class="toolbar-btn" onclick="ImageEditorStandalone.instance.rotate(90)" title="右に90度回転">
                                <span class="material-icons">rotate_right</span>
                                <span>右回転</span>
                            </button>
                        </div>

                        <div class="toolbar-group">
                            <button class="toolbar-btn" onclick="ImageEditorStandalone.instance.flipHorizontal()" title="左右反転">
                                <span class="material-icons">flip</span>
                                <span>左右反転</span>
                            </button>
                            <button class="toolbar-btn" onclick="ImageEditorStandalone.instance.flipVertical()" title="上下反転">
                                <span class="material-icons" style="transform: rotate(90deg)">flip</span>
                                <span>上下反転</span>
                            </button>
                        </div>

                        <div class="toolbar-group">
                            <button class="toolbar-btn" onclick="ImageEditorStandalone.instance.reset()" title="リセット">
                                <span class="material-icons">refresh</span>
                                <span>リセット</span>
                            </button>
                        </div>
                    </div>

                    <div class="image-editor-canvas-wrapper">
                        <canvas id="imageEditorCanvas" class="image-editor-canvas"></canvas>
                        <div id="imageEditorLoading" class="image-editor-loading">
                            <span class="material-icons rotating">refresh</span>
                            <p>読み込み中...</p>
                        </div>
                    </div>

                    <div class="image-editor-info">
                        <span id="imageEditorDimensions">-</span>
                        <span id="imageEditorRotation">回転: 0°</span>
                    </div>

                    <div class="image-editor-footer">
                        <button class="image-editor-btn image-editor-btn-secondary" onclick="ImageEditorStandalone.instance.close()">
                            キャンセル
                        </button>
                        <button class="image-editor-btn image-editor-btn-primary" onclick="ImageEditorStandalone.instance.save()">
                            <span class="material-icons">save</span>
                            保存
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Close image editor modal
     */
    close() {
        const modal = document.getElementById('imageEditorModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }

        if (this.config.onCancel && typeof this.config.onCancel === 'function') {
            this.config.onCancel();
        }

        // Reset state
        this.currentImage = null;
        this.currentRotation = 0;
        this.originalImageData = null;
    }

    /**
     * Load image into canvas
     */
    async loadImage(imageUrl) {
        const loading = document.getElementById('imageEditorLoading');
        const canvas = document.getElementById('imageEditorCanvas');

        if (loading) loading.style.display = 'flex';

        try {
            const img = new Image();
            img.crossOrigin = 'anonymous';

            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = imageUrl;
            });

            this.currentImage = img;
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');

            // Set canvas size
            canvas.width = img.width;
            canvas.height = img.height;

            // Draw image
            this.ctx.drawImage(img, 0, 0);

            // Store original image data
            this.originalImageData = this.ctx.getImageData(0, 0, canvas.width, canvas.height);

            // Update info
            this.updateInfo();

            if (loading) loading.style.display = 'none';

        } catch (error) {
            console.error('Failed to load image:', error);
            alert('画像の読み込みに失敗しました');
            this.close();
        }
    }

    /**
     * Rotate image
     */
    rotate(degrees) {
        if (!this.canvas || !this.ctx || !this.currentImage) return;

        this.currentRotation = (this.currentRotation + degrees) % 360;
        if (this.currentRotation < 0) this.currentRotation += 360;

        this.redrawCanvas();
        this.updateInfo();
    }

    /**
     * Flip image horizontally
     */
    flipHorizontal() {
        if (!this.canvas || !this.ctx) return;

        this.ctx.scale(-1, 1);
        this.ctx.drawImage(this.canvas, -this.canvas.width, 0);
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    }

    /**
     * Flip image vertically
     */
    flipVertical() {
        if (!this.canvas || !this.ctx) return;

        this.ctx.scale(1, -1);
        this.ctx.drawImage(this.canvas, 0, -this.canvas.height);
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    }

    /**
     * Reset to original image
     */
    reset() {
        if (!this.canvas || !this.ctx || !this.originalImageData) return;

        this.currentRotation = 0;
        this.ctx.putImageData(this.originalImageData, 0, 0);
        this.updateInfo();
    }

    /**
     * Redraw canvas with current rotation
     */
    redrawCanvas() {
        if (!this.canvas || !this.ctx || !this.currentImage) return;

        const rotation = (this.currentRotation * Math.PI) / 180;

        // Calculate new dimensions for 90/270 degree rotations
        let newWidth = this.currentImage.width;
        let newHeight = this.currentImage.height;

        if (this.currentRotation === 90 || this.currentRotation === 270) {
            newWidth = this.currentImage.height;
            newHeight = this.currentImage.width;
        }

        // Resize canvas
        this.canvas.width = newWidth;
        this.canvas.height = newHeight;

        // Clear canvas
        this.ctx.clearRect(0, 0, newWidth, newHeight);

        // Save context
        this.ctx.save();

        // Move to center
        this.ctx.translate(newWidth / 2, newHeight / 2);

        // Rotate
        this.ctx.rotate(rotation);

        // Draw image centered
        this.ctx.drawImage(
            this.currentImage,
            -this.currentImage.width / 2,
            -this.currentImage.height / 2
        );

        // Restore context
        this.ctx.restore();
    }

    /**
     * Update info display
     */
    updateInfo() {
        const dimensionsEl = document.getElementById('imageEditorDimensions');
        const rotationEl = document.getElementById('imageEditorRotation');

        if (dimensionsEl && this.canvas) {
            dimensionsEl.textContent = `${this.canvas.width} × ${this.canvas.height}`;
        }

        if (rotationEl) {
            rotationEl.textContent = `回転: ${this.currentRotation}°`;
        }
    }

    /**
     * Save edited image
     */
    async save() {
        if (!this.canvas) {
            alert('画像が読み込まれていません');
            return;
        }

        try {
            // Convert canvas to blob
            const blob = await new Promise(resolve => {
                this.canvas.toBlob(resolve, 'image/png');
            });

            // If mediaId is provided, update via API
            if (this.config.mediaId) {
                await this.saveToMedia(blob);
            }

            // Call onSave callback
            if (this.config.onSave && typeof this.config.onSave === 'function') {
                const dataUrl = this.canvas.toDataURL('image/png');
                this.config.onSave({
                    blob: blob,
                    dataUrl: dataUrl,
                    rotation: this.currentRotation
                });
            }

            alert('画像を保存しました');
            this.close();

        } catch (error) {
            console.error('Failed to save image:', error);
            alert('画像の保存に失敗しました: ' + error.message);
        }
    }

    /**
     * Save edited image to media library
     */
    async saveToMedia(blob) {
        const formData = new FormData();
        formData.append('file', blob, 'edited_image.png');
        formData.append('media_type', 'image');
        formData.append('title', `Edited Image ${Date.now()}`);
        formData.append('source_media_id', this.config.mediaId);

        const response = await fetch('/api/media/upload', {
            method: 'POST',
            credentials: 'same-origin',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to upload edited image');
        }

        return await response.json();
    }
}

// Create global instance
ImageEditorStandalone.instance = new ImageEditorStandalone();

// Expose for inline onclick handlers
window.ImageEditorStandalone = ImageEditorStandalone.instance;
