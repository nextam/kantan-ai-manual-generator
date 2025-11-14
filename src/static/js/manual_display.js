/**
 * File: manual_display.js
 * Purpose: Manual content display and tab management
 * Main functionality: Display manual content, handle multi-stage tabs, format rendering
 * Dependencies: marked.js for Markdown rendering
 */

class ManualDisplay {
    constructor() {
        this.currentManual = null;
        this.activeTab = 'stage3';
    }

    /**
     * Display manual content
     * @param {Object} manual - Manual object
     */
    displayManual(manual) {
        console.log('=== displayManual start ===');
        console.log('manual:', manual);

        this.currentManual = manual;

        // Hide loading
        document.getElementById('loading').style.display = 'none';

        // Set title
        document.title = manual.title + ' - マニュアル詳細';

        // Set metadata
        document.getElementById('created-date').textContent = this.formatDate(manual.created_at);
        document.getElementById('output-format').textContent = this.getFormatText(manual.output_format);

        // Determine display mode
        const hasStageContent = manual.stage1_content && manual.stage2_content && manual.stage3_content;
        console.log('hasStageContent:', hasStageContent);

        if (hasStageContent) {
            // Multi-stage manual (manual_with_images)
            console.log('Displaying as multi-stage manual');
            this.displayMultiStageManual(manual);
        } else {
            // Normal single manual
            console.log('Displaying as single manual');
            this.displaySingleManual(manual);
        }

        // Display videos
        if (manual.source_videos && manual.source_videos.length > 0) {
            console.log('Displaying videos:', manual.source_videos.length);
            videoDisplay.displayVideos(
                manual.source_videos, 
                manual.manual_type || 'basic',
                manual.output_format
            );
        }

        // Display video clips if format is text_with_video_clips
        if (manual.output_format === 'text_with_video_clips' && manual.video_clips && manual.video_clips.length > 0) {
            console.log('Displaying video clips:', manual.video_clips.length);
            const sourceVideoUrl = manual.source_videos && manual.source_videos[0] ? manual.source_videos[0].url : null;
            videoDisplay.displayVideoClips(manual.video_clips, sourceVideoUrl);
        }

        // Initialize image editor for text_with_images format
        if ((manual.output_format === 'text_with_images' || manual.output_format === 'hybrid') && 
            manual.extracted_images && manual.extracted_images.length > 0) {
            console.log('Initializing image editor with', manual.extracted_images.length, 'images');
            setTimeout(() => {
                imageEditor.init(manual);
                imageEditor.loadRotationStates();
            }, 500); // Delay to ensure DOM is ready
        }
    }

    /**
     * Display multi-stage manual (with images)
     * @param {Object} manual - Manual object
     */
    displayMultiStageManual(manual) {
        document.getElementById('multi-stage-tabs').style.display = 'block';
        document.getElementById('normal-manual').style.display = 'none';

        // Display each stage
        this.displayStageContent(manual.stage1_content, 'stage1-text');
        this.displayStageContent(manual.stage2_content, 'stage2-text');
        this.displayStageContent(manual.stage3_content, 'stage3-text');

        // Setup tab switching
        this.setupTabSwitching();
    }

    /**
     * Display single manual content
     * @param {Object} manual - Manual object
     */
    displaySingleManual(manual) {
        document.getElementById('multi-stage-tabs').style.display = 'none';
        document.getElementById('normal-manual').style.display = 'block';

        const content = manual.content || manual.content_html || manual.content_text || '';
        this.displayContent(content, 'manual-text');
    }

    /**
     * Display stage content (for multi-stage)
     * @param {string} content - Content to display
     * @param {string} elementId - Target element ID
     */
    displayStageContent(content, elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error('Element not found:', elementId);
            return;
        }

        this.displayContent(content, elementId);
    }

    /**
     * Display content with markdown/HTML rendering
     * @param {string} content - Content to display
     * @param {string} elementId - Target element ID
     */
    displayContent(content, elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error('Element not found:', elementId);
            return;
        }

        if (!content) {
            element.innerHTML = '<p style="color: #666;">コンテンツがありません</p>';
            return;
        }

        // Check if content is HTML or Markdown
        if (content.trim().startsWith('<')) {
            // HTML content
            element.innerHTML = content;
        } else {
            // Markdown content - use marked.js
            if (typeof marked !== 'undefined') {
                element.innerHTML = marked.parse(content);
            } else {
                // Fallback: display as pre-formatted text
                element.innerHTML = `<pre style="white-space: pre-wrap; word-wrap: break-word;">${this.escapeHtml(content)}</pre>`;
            }
        }

        console.log(`Content displayed in ${elementId}`);
    }

    /**
     * Setup tab switching for multi-stage manual
     */
    setupTabSwitching() {
        const tabHeaders = document.querySelectorAll('.tab-header');
        const tabContents = document.querySelectorAll('.tab-content');

        tabHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const targetTab = header.dataset.tab;

                // Remove active class from all
                tabHeaders.forEach(h => h.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                // Add active class to clicked
                header.classList.add('active');
                document.getElementById(`tab-${targetTab}`).classList.add('active');

                this.activeTab = targetTab;
                console.log('Switched to tab:', targetTab);
            });
        });
    }

    /**
     * Get human-readable format text
     * @param {string} format - Output format code
     * @returns {string} Formatted text
     */
    getFormatText(format) {
        const formatMap = {
            'text_only': 'テキストのみ',
            'text_with_images': 'テキスト + 画像',
            'text_with_video_clips': 'テキスト + 動画クリップ',
            'subtitle_video': '字幕付き動画',
            'hybrid': 'ハイブリッド'
        };
        return formatMap[format] || format || 'テキスト + 画像';
    }

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        if (!dateString) return '未設定';

        let date;
        if (dateString.includes('T') && !dateString.includes('+') && !dateString.includes('Z')) {
            date = new Date(dateString + '+09:00');
        } else {
            date = new Date(dateString);
        }

        return date.toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Escape HTML for safe display
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        document.getElementById('loading').innerHTML = `
            <div style="color: #dc3545; font-weight: bold;">
                <span class="material-icons" style="font-size: 16px; vertical-align: middle; margin-right: 5px;">error</span>${message}
            </div>
            <div style="margin-top: 20px;">
                <a href="/manual/list" class="btn btn-secondary">
                    <span class="material-icons">arrow_back</span>一覧に戻る
                </a>
            </div>
        `;
    }
}

// Create global instance
const manualDisplay = new ManualDisplay();
