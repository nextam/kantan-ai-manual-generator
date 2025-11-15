/**
 * File: media_library.js
 * Purpose: Reusable media library component with WordPress-like interface
 * Main functionality: Modal control, API integration, media selection, upload, capture
 * Dependencies: Fetch API, DOM manipulation
 */

class MediaLibrary {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.selectedMedia = null;
        this.config = {};
        this.mediaCache = [];
        this.filters = {
            mediaType: '',
            search: '',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };
    }

    /**
     * Open media library modal
     * @param {Object} config - Configuration options
     * @param {string} config.mode - 'select' or 'manage'
     * @param {string} config.mediaType - 'image', 'video', or null for all
     * @param {Function} config.onSelect - Callback when media is selected
     * @param {Function} config.onEdit - Callback when edit is triggered
     */
    open(config = {}) {
        this.config = {
            mode: config.mode || 'select',
            mediaType: config.mediaType || null,
            onSelect: config.onSelect || null,
            onEdit: config.onEdit || null,
            allowMultiple: config.allowMultiple || false
        };

        // Reset state
        this.currentPage = 1;
        this.selectedMedia = null;
        this.filters.mediaType = this.config.mediaType || '';

        // Show modal
        const modal = document.getElementById('mediaLibraryModal');
        if (!modal) {
            console.error('Media library modal not found');
            return;
        }

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Load media
        this.loadMedia();
    }

    /**
     * Close media library modal
     */
    close() {
        const modal = document.getElementById('mediaLibraryModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }

        // Reset state
        this.selectedMedia = null;
        this.hideDetailsPanel();
    }

    /**
     * Load media list from API
     */
    async loadMedia(page = 1) {
        this.currentPage = page;
        
        const loadingEl = document.getElementById('mediaLoading');
        const gridEl = document.getElementById('mediaGrid');
        const emptyStateEl = document.getElementById('mediaEmptyState');

        if (loadingEl) loadingEl.style.display = 'flex';
        if (gridEl) gridEl.innerHTML = '';
        if (emptyStateEl) emptyStateEl.style.display = 'none';

        try {
            // Build query parameters
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                sort_by: this.filters.sortBy,
                sort_order: this.filters.sortOrder
            });

            if (this.filters.mediaType) {
                params.append('media_type', this.filters.mediaType);
            }

            if (this.filters.search) {
                params.append('search', this.filters.search);
            }

            const response = await fetch(`/api/media/library?${params}`, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.mediaCache = data.items || [];

            if (loadingEl) loadingEl.style.display = 'none';

            if (this.mediaCache.length === 0) {
                if (emptyStateEl) emptyStateEl.style.display = 'flex';
            } else {
                this.renderMediaGrid(this.mediaCache);
                this.renderPagination(data);
            }

        } catch (error) {
            console.error('Failed to load media:', error);
            if (loadingEl) loadingEl.style.display = 'none';
            if (emptyStateEl) {
                emptyStateEl.style.display = 'flex';
                emptyStateEl.innerHTML = `
                    <span class="material-icons">error</span>
                    <p>メディアの読み込みに失敗しました</p>
                    <p style="color: #999; font-size: 12px;">${error.message}</p>
                `;
            }
        }
    }

    /**
     * Render media grid
     */
    renderMediaGrid(items) {
        const gridEl = document.getElementById('mediaGrid');
        if (!gridEl) return;

        gridEl.innerHTML = items.map(media => {
            const isVideo = media.media_type === 'video';
            const thumbnailUrl = media.signed_url;

            return `
                <div class="media-item ${this.selectedMedia?.id === media.id ? 'selected' : ''}" 
                     data-media-id="${media.id}"
                     onclick="MediaLibrary.instance.selectMediaItem(${media.id})">
                    <div class="media-item-thumbnail">
                        ${isVideo ? `
                            <video src="${thumbnailUrl}" preload="metadata"></video>
                            <div class="media-type-badge">
                                <span class="material-icons">videocam</span>
                            </div>
                        ` : `
                            <img src="${thumbnailUrl}" alt="${media.title || media.filename}" loading="lazy">
                        `}
                        <div class="media-item-overlay">
                            <button class="media-item-action" onclick="event.stopPropagation(); MediaLibrary.instance.showMediaDetails(${media.id});" title="詳細">
                                <span class="material-icons">info</span>
                            </button>
                            ${!isVideo ? `
                                <button class="media-item-action" onclick="event.stopPropagation(); MediaLibrary.instance.editMedia(${media.id});" title="編集">
                                    <span class="material-icons">edit</span>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="media-item-info">
                        <div class="media-item-title">${this.truncateText(media.title || media.filename, 20)}</div>
                        <div class="media-item-meta">${this.formatFileSize(media.file_size)}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Render pagination
     */
    renderPagination(data) {
        const paginationEl = document.getElementById('mediaPagination');
        if (!paginationEl) return;

        if (data.total_pages <= 1) {
            paginationEl.innerHTML = '';
            return;
        }

        const pages = [];
        const currentPage = data.page;
        const totalPages = data.total_pages;

        // Previous button
        pages.push(`
            <button class="pagination-btn" 
                    ${!data.has_prev ? 'disabled' : ''} 
                    onclick="MediaLibrary.instance.loadMedia(${currentPage - 1})">
                <span class="material-icons">chevron_left</span>
            </button>
        `);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                pages.push(`
                    <button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                            onclick="MediaLibrary.instance.loadMedia(${i})">
                        ${i}
                    </button>
                `);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                pages.push('<span class="pagination-ellipsis">...</span>');
            }
        }

        // Next button
        pages.push(`
            <button class="pagination-btn" 
                    ${!data.has_next ? 'disabled' : ''} 
                    onclick="MediaLibrary.instance.loadMedia(${currentPage + 1})">
                <span class="material-icons">chevron_right</span>
            </button>
        `);

        paginationEl.innerHTML = pages.join('');
    }

    /**
     * Select media item
     */
    selectMediaItem(mediaId) {
        const media = this.mediaCache.find(m => m.id === mediaId);
        if (!media) return;

        this.selectedMedia = media;

        // Update UI
        document.querySelectorAll('.media-item').forEach(item => {
            item.classList.remove('selected');
        });
        const selectedItem = document.querySelector(`.media-item[data-media-id="${mediaId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // Update selection info
        const selectionInfo = document.getElementById('mediaSelectionInfo');
        const selectButton = document.getElementById('mediaSelectButton');
        
        if (selectionInfo) {
            selectionInfo.textContent = `選択済み: ${media.title || media.filename}`;
        }
        if (selectButton) {
            selectButton.disabled = false;
        }

        // Show details panel in manage mode
        if (this.config.mode === 'manage') {
            this.showMediaDetails(mediaId);
        }
    }

    /**
     * Select and return media (callback)
     */
    selectMedia() {
        if (!this.selectedMedia) return;

        if (this.config.onSelect && typeof this.config.onSelect === 'function') {
            this.config.onSelect(this.selectedMedia);
        }

        this.close();
    }

    /**
     * Show media details panel
     */
    async showMediaDetails(mediaId) {
        try {
            const response = await fetch(`/api/media/${mediaId}`, {
                method: 'GET',
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to load media details');
            }

            const data = await response.json();
            const media = data.media;

            // Populate form
            document.getElementById('mediaDetailTitle').value = media.title || '';
            document.getElementById('mediaDetailDescription').value = media.description || '';
            document.getElementById('mediaDetailAltText').value = media.alt_text || '';
            document.getElementById('mediaDetailTags').value = (media.tags || []).join(', ');

            // File info
            document.getElementById('mediaDetailFilename').textContent = media.filename;
            document.getElementById('mediaDetailSize').textContent = this.formatFileSize(media.file_size);
            
            if (media.image_metadata) {
                const dimensions = `${media.image_metadata.width || 0} × ${media.image_metadata.height || 0}`;
                document.getElementById('mediaDetailDimensions').textContent = dimensions;
            }
            document.getElementById('mediaDetailCreatedAt').textContent = new Date(media.created_at).toLocaleString('ja-JP');

            // Preview
            const imagePreview = document.getElementById('mediaDetailImage');
            const videoPreview = document.getElementById('mediaDetailVideo');
            
            if (media.media_type === 'image') {
                imagePreview.src = media.signed_url;
                imagePreview.style.display = 'block';
                videoPreview.style.display = 'none';
            } else if (media.media_type === 'video') {
                videoPreview.src = media.signed_url;
                videoPreview.style.display = 'block';
                imagePreview.style.display = 'none';
            }

            // Show panel
            const detailsPanel = document.getElementById('mediaDetailsPanel');
            if (detailsPanel) {
                detailsPanel.style.display = 'block';
                detailsPanel.dataset.mediaId = mediaId;
            }

        } catch (error) {
            console.error('Failed to show media details:', error);
            alert('メディア詳細の読み込みに失敗しました');
        }
    }

    /**
     * Hide details panel
     */
    hideDetailsPanel() {
        const detailsPanel = document.getElementById('mediaDetailsPanel');
        if (detailsPanel) {
            detailsPanel.style.display = 'none';
            delete detailsPanel.dataset.mediaId;
        }
    }

    /**
     * Update media details
     */
    async updateMediaDetails() {
        const detailsPanel = document.getElementById('mediaDetailsPanel');
        if (!detailsPanel || !detailsPanel.dataset.mediaId) return;

        const mediaId = parseInt(detailsPanel.dataset.mediaId);
        
        const title = document.getElementById('mediaDetailTitle').value;
        const description = document.getElementById('mediaDetailDescription').value;
        const altText = document.getElementById('mediaDetailAltText').value;
        const tagsStr = document.getElementById('mediaDetailTags').value;
        const tags = tagsStr.split(',').map(t => t.trim()).filter(t => t);

        try {
            const response = await fetch(`/api/media/${mediaId}`, {
                method: 'PUT',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title,
                    description,
                    alt_text: altText,
                    tags
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update media');
            }

            alert('メディア情報を更新しました');
            this.loadMedia(this.currentPage);

        } catch (error) {
            console.error('Failed to update media:', error);
            alert('更新に失敗しました: ' + error.message);
        }
    }

    /**
     * Delete media
     */
    async deleteMedia() {
        const detailsPanel = document.getElementById('mediaDetailsPanel');
        if (!detailsPanel || !detailsPanel.dataset.mediaId) return;

        const mediaId = parseInt(detailsPanel.dataset.mediaId);

        if (!confirm('このメディアを削除してもよろしいですか?')) {
            return;
        }

        try {
            const response = await fetch(`/api/media/${mediaId}`, {
                method: 'DELETE',
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to delete media');
            }

            alert('メディアを削除しました');
            this.hideDetailsPanel();
            this.loadMedia(this.currentPage);

        } catch (error) {
            console.error('Failed to delete media:', error);
            alert('削除に失敗しました: ' + error.message);
        }
    }

    /**
     * Edit media (open image editor)
     */
    editMedia(mediaId) {
        if (!mediaId && this.selectedMedia) {
            mediaId = this.selectedMedia.id;
        }

        const media = this.mediaCache.find(m => m.id === mediaId);
        if (!media) return;

        if (media.media_type !== 'image') {
            alert('画像編集は画像ファイルのみ対応しています');
            return;
        }

        // Call image editor if available
        if (window.ImageEditorStandalone) {
            window.ImageEditorStandalone.open({
                imageUrl: media.signed_url,
                mediaId: media.id,
                onSave: (editedImageData) => {
                    // Reload media after edit
                    this.loadMedia(this.currentPage);
                }
            });
        } else if (this.config.onEdit && typeof this.config.onEdit === 'function') {
            this.config.onEdit(media);
        } else {
            alert('画像編集機能が利用できません');
        }
    }

    /**
     * Search media
     */
    search() {
        const searchInput = document.getElementById('mediaSearchInput');
        if (!searchInput) return;

        this.filters.search = searchInput.value;
        this.currentPage = 1;
        this.loadMedia();
    }

    /**
     * Apply filters
     */
    applyFilters() {
        const typeFilter = document.getElementById('mediaTypeFilter');
        const sortFilter = document.getElementById('mediaSortFilter');

        if (typeFilter) {
            this.filters.mediaType = typeFilter.value;
        }

        if (sortFilter) {
            const sortValue = sortFilter.value.split('_');
            this.filters.sortBy = sortValue[0];
            this.filters.sortOrder = sortValue[1];
        }

        this.currentPage = 1;
        this.loadMedia();
    }

    /**
     * Open upload dialog
     */
    openUploadDialog() {
        const dialog = document.getElementById('mediaUploadDialog');
        if (!dialog) return;

        dialog.style.display = 'flex';
        
        // Reset form
        document.getElementById('mediaFileInput').value = '';
        document.getElementById('uploadTitle').value = '';
        document.getElementById('uploadDescription').value = '';
        document.getElementById('uploadTags').value = '';
        document.getElementById('uploadPreviewArea').style.display = 'none';
        document.getElementById('uploadSubmitButton').disabled = true;
    }

    /**
     * Close upload dialog
     */
    closeUploadDialog() {
        const dialog = document.getElementById('mediaUploadDialog');
        if (dialog) {
            dialog.style.display = 'none';
        }
    }

    /**
     * Handle file select
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Show preview
        const previewArea = document.getElementById('uploadPreviewArea');
        const previewImage = document.getElementById('uploadPreviewImage');
        const titleInput = document.getElementById('uploadTitle');
        const submitButton = document.getElementById('uploadSubmitButton');

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                previewArea.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }

        // Set default title
        if (!titleInput.value) {
            titleInput.value = file.name.replace(/\.[^/.]+$/, '');
        }

        submitButton.disabled = false;
    }

    /**
     * Upload file
     */
    async uploadFile() {
        const fileInput = document.getElementById('mediaFileInput');
        const file = fileInput.files[0];
        if (!file) return;

        const title = document.getElementById('uploadTitle').value;
        const description = document.getElementById('uploadDescription').value;
        const tagsStr = document.getElementById('uploadTags').value;
        const tags = tagsStr.split(',').map(t => t.trim()).filter(t => t);

        // Determine media type
        const mediaType = file.type.startsWith('image/') ? 'image' : 'video';

        // Show progress
        const progressEl = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('uploadProgressFill');
        const progressText = document.getElementById('uploadProgressText');
        
        if (progressEl) progressEl.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = 'アップロード中... 0%';

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('media_type', mediaType);
            formData.append('title', title);
            formData.append('description', description);
            formData.append('tags', JSON.stringify(tags));

            const response = await fetch('/api/media/upload', {
                method: 'POST',
                credentials: 'same-origin',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Upload failed');
            }

            const data = await response.json();
            
            if (progressFill) progressFill.style.width = '100%';
            if (progressText) progressText.textContent = 'アップロード完了!';

            setTimeout(() => {
                this.closeUploadDialog();
                this.loadMedia(this.currentPage);
                alert('メディアをアップロードしました');
            }, 500);

        } catch (error) {
            console.error('Upload failed:', error);
            alert('アップロードに失敗しました: ' + error.message);
            if (progressEl) progressEl.style.display = 'none';
        }
    }

    /**
     * Open capture dialog
     */
    async openCaptureDialog() {
        const dialog = document.getElementById('mediaCaptureDialog');
        if (!dialog) return;

        dialog.style.display = 'flex';

        // Load video list
        await this.loadVideoList();
    }

    /**
     * Close capture dialog
     */
    closeCaptureDialog() {
        const dialog = document.getElementById('mediaCaptureDialog');
        if (dialog) {
            dialog.style.display = 'none';
        }

        // Stop video
        const video = document.getElementById('captureVideo');
        if (video) {
            video.pause();
            video.src = '';
        }
    }

    /**
     * Load video list for capture
     */
    async loadVideoList() {
        try {
            const response = await fetch('/api/media/library?media_type=video&per_page=100', {
                method: 'GET',
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to load videos');
            }

            const data = await response.json();
            const select = document.getElementById('captureVideoSelect');
            
            if (select) {
                select.innerHTML = '<option value="">動画を選択してください</option>' +
                    data.items.map(video => 
                        `<option value="${video.id}" data-url="${video.signed_url}">${video.title || video.filename}</option>`
                    ).join('');
            }

        } catch (error) {
            console.error('Failed to load videos:', error);
            alert('動画一覧の読み込みに失敗しました');
        }
    }

    /**
     * Load capture video
     */
    loadCaptureVideo() {
        const select = document.getElementById('captureVideoSelect');
        if (!select || !select.value) return;

        const option = select.options[select.selectedIndex];
        const videoUrl = option.dataset.url;
        
        const video = document.getElementById('captureVideo');
        const player = document.getElementById('captureVideoPlayer');
        
        if (video && player) {
            video.src = videoUrl;
            player.style.display = 'block';
            
            // Update timestamp display
            video.addEventListener('timeupdate', () => {
                const timestamp = document.getElementById('captureTimestamp');
                if (timestamp) {
                    const minutes = Math.floor(video.currentTime / 60);
                    const seconds = Math.floor(video.currentTime % 60);
                    timestamp.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }
            });
        }
    }

    /**
     * Capture current frame
     */
    async captureCurrentFrame() {
        const video = document.getElementById('captureVideo');
        const select = document.getElementById('captureVideoSelect');
        
        if (!video || !select || !select.value) return;

        const videoMediaId = parseInt(select.value);
        const timestamp = video.currentTime;

        // Create canvas to capture frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        // Show preview
        const preview = document.getElementById('capturedFramePreview');
        const metadata = document.getElementById('captureMetadata');
        const saveButton = document.getElementById('captureSaveButton');
        
        if (preview) {
            preview.src = canvas.toDataURL('image/png');
        }
        if (metadata) {
            metadata.style.display = 'block';
        }
        if (saveButton) {
            saveButton.disabled = false;
        }

        // Store capture data
        this.captureData = {
            videoMediaId,
            timestamp,
            imageData: canvas.toDataURL('image/png')
        };
    }

    /**
     * Save captured frame
     */
    async saveCapture() {
        if (!this.captureData) return;

        const title = document.getElementById('captureTitle').value || `Frame at ${this.captureData.timestamp.toFixed(1)}s`;
        const description = document.getElementById('captureDescription').value;

        try {
            const response = await fetch('/api/media/capture-frame', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_media_id: this.captureData.videoMediaId,
                    timestamp: this.captureData.timestamp,
                    title,
                    description
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save capture');
            }

            alert('フレームをキャプチャしました');
            this.closeCaptureDialog();
            this.loadMedia(this.currentPage);

        } catch (error) {
            console.error('Failed to save capture:', error);
            alert('キャプチャの保存に失敗しました: ' + error.message);
        }
    }

    // Utility functions

    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

// Create global instance
MediaLibrary.instance = new MediaLibrary();

// Expose for inline onclick handlers
window.MediaLibrary = MediaLibrary.instance;
