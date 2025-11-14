/**
 * File: video_display.js
 * Purpose: Video display and clip playback functionality for manual detail page with HLS support
 * Main functionality: Display source videos, support video clip playback with time ranges, HLS adaptive streaming
 * Dependencies: HLS.js (loaded from CDN)
 */

class VideoDisplay {
    constructor() {
        this.videoSection = null;
        this.videoGrid = null;
        this.currentManual = null;
        this.hlsInstances = new Map(); // Track HLS instances for cleanup
        this.hlsLoaded = false;
        this._loadHlsLibrary();
    }
    
    /**
     * Load HLS.js library from CDN
     */
    _loadHlsLibrary() {
        if (window.Hls) {
            this.hlsLoaded = true;
            console.log('HLS.js already loaded');
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/hls.js@latest';
        script.onload = () => {
            this.hlsLoaded = true;
            console.log('HLS.js loaded successfully');
        };
        script.onerror = () => {
            console.error('Failed to load HLS.js');
        };
        document.head.appendChild(script);
    }
    
    /**
     * Check if URL is HLS manifest
     */
    _isHlsUrl(url) {
        return url && (url.endsWith('.m3u8') || url.includes('master.m3u8'));
    }
    
    /**
     * Setup video player with HLS support
     */
    _setupVideoPlayer(videoElement, videoUrl) {
        if (!videoUrl) {
            console.error('No video URL provided');
            return false;
        }
        
        const videoId = videoElement.id || `video_${Date.now()}`;
        videoElement.id = videoId;
        
        // Clean up existing HLS instance if any
        this._cleanupHlsInstance(videoId);
        
        // Check if HLS
        if (this._isHlsUrl(videoUrl)) {
            return this._setupHlsPlayer(videoElement, videoUrl, videoId);
        } else {
            // Regular MP4 video
            videoElement.src = videoUrl;
            return true;
        }
    }
    
    /**
     * Setup HLS player
     */
    _setupHlsPlayer(videoElement, hlsUrl, videoId) {
        // Safari native HLS support
        if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
            console.log('Using native HLS support (Safari)');
            videoElement.src = hlsUrl;
            return true;
        }
        
        // HLS.js for other browsers
        if (window.Hls && Hls.isSupported()) {
            console.log('Using HLS.js for:', videoId);
            
            const hls = new Hls({
                enableWorker: true,
                lowLatencyMode: false,
                backBufferLength: 90
            });
            
            hls.loadSource(hlsUrl);
            hls.attachMedia(videoElement);
            
            // Event listeners
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                console.log('HLS manifest loaded, qualities:', hls.levels.length);
            });
            
            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    console.error('Fatal HLS error:', data);
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.error('Network error, trying to recover...');
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.error('Media error, trying to recover...');
                            hls.recoverMediaError();
                            break;
                        default:
                            console.error('Unrecoverable error, destroying HLS instance');
                            hls.destroy();
                            break;
                    }
                }
            });
            
            // Store instance for cleanup
            this.hlsInstances.set(videoId, hls);
            
            return true;
        }
        
        console.warn('HLS not supported, falling back to src');
        videoElement.src = hlsUrl;
        return false;
    }
    
    /**
     * Cleanup HLS instances
     */
    _cleanupHlsInstance(videoId) {
        if (this.hlsInstances.has(videoId)) {
            const hls = this.hlsInstances.get(videoId);
            hls.destroy();
            this.hlsInstances.delete(videoId);
            console.log(`HLS instance cleaned up: ${videoId}`);
        }
    }

    /**
     * Initialize video display components
     */
    init() {
        this.videoSection = document.getElementById('video-section');
        this.videoGrid = document.getElementById('video-grid');
    }

    /**
     * Display source videos
     * @param {Array} videos - Array of video objects
     * @param {string} manualType - Type of manual
     * @param {string} outputFormat - Output format (text_with_video_clips, etc.)
     */
    displayVideos(videos, manualType, outputFormat) {
        console.log('displayVideos:', { videos, manualType, outputFormat });
        
        if (!videos || videos.length === 0) {
            console.log('No videos to display');
            this.videoSection.style.display = 'none';
            return;
        }

        let videosHtml = '';
        videos.forEach(video => {
            if (!video.url) {
                console.warn('Video URL is empty, skipping:', video);
                return;
            }
            
            const isExpert = video.type === 'expert';
            const labelClass = isExpert ? 'expert-label' : 'novice-label';
            const hideNoviceLabel = (manualType === 'manual_with_images') && !isExpert;
            const labelText = isExpert
                ? '<span class="material-icons" style="font-size: 20px; vertical-align: middle; margin-right: 5px;">star</span>熟練者動画'
                : (hideNoviceLabel ? '' : '<span class="material-icons" style="font-size: 20px; vertical-align: middle; margin-right: 5px;">school</span>非熟練者動画');

            const videoId = `source-video-${video.file_id}`;
            videosHtml += `
                <div class="video-item">
                    ${hideNoviceLabel ? '' : `<div class="video-label ${labelClass}">${labelText}</div>`}
                    <video controls id="${videoId}" data-video-id="${video.file_id}" data-video-url="${video.url}">
                        お使いのブラウザは動画タグをサポートしていません。
                    </video>
                    <div style="margin-top: 10px; font-size: 14px; color: #666;">
                        <div><strong>ファイル名:</strong> ${video.filename}</div>
                        ${video.duration ? `<div><strong>長さ:</strong> ${video.duration}</div>` : ''}
                    </div>
                </div>
            `;
        });

        this.videoGrid.innerHTML = videosHtml;
        
        // Setup HLS for each video after DOM insertion
        videos.forEach(video => {
            if (video.url) {
                const videoId = `source-video-${video.file_id}`;
                const videoElement = document.getElementById(videoId);
                if (videoElement) {
                    this._setupVideoPlayer(videoElement, video.url);
                }
            }
        });
        
        if (manualType === 'manual_with_images') {
            this.videoGrid.querySelectorAll('.video-item').forEach(item => {
                const label = item.querySelector('.video-label');
                if (!label) {
                    item.style.paddingTop = '10px';
                }
            });
        }
        
        this.videoSection.style.display = 'block';
    }

    /**
     * Display video clips section for text_with_video_clips format
     * @param {Array} clips - Array of video clip objects with time ranges
     * @param {string} sourceVideoUrl - URL of the source video
     */
    displayVideoClips(clips, sourceVideoUrl) {
        console.log('displayVideoClips:', { clips, sourceVideoUrl });
        
        if (!clips || clips.length === 0) {
            console.log('No video clips to display');
            return;
        }

        // Create clips section if it doesn't exist
        let clipsSection = document.getElementById('video-clips-section');
        if (!clipsSection) {
            clipsSection = document.createElement('div');
            clipsSection.id = 'video-clips-section';
            clipsSection.className = 'video-clips-section';
            clipsSection.innerHTML = `
                <h3>
                    <span class="material-icons">movie</span>
                    作業手順動画クリップ
                </h3>
                <div id="video-clips-grid" class="video-clips-grid"></div>
            `;
            
            // Insert after video-section or before manual-content
            const manualContent = document.querySelector('.manual-content');
            manualContent.parentNode.insertBefore(clipsSection, manualContent);
        }

        const clipsGrid = document.getElementById('video-clips-grid');
        let clipsHtml = '';

        clips.forEach((clip, index) => {
            const clipId = `video-clip-${index}`;
            clipsHtml += `
                <div class="video-clip-item">
                    <div class="clip-header">
                        <span class="clip-number">Step ${clip.step_number || (index + 1)}</span>
                        <span class="clip-title">${clip.step_title || 'ステップ ' + (index + 1)}</span>
                    </div>
                    <div class="clip-time-range">
                        ${clip.start_formatted || this.formatTime(clip.start_time)} - ${clip.end_formatted || this.formatTime(clip.end_time)}
                        (${Math.round(clip.duration || (clip.end_time - clip.start_time))}秒)
                    </div>
                    <video 
                        controls 
                        id="${clipId}" 
                        class="clip-video"
                        data-start="${clip.start_time}"
                        data-end="${clip.end_time}">
                        <source src="${clip.video_uri || sourceVideoUrl}" type="video/mp4">
                    </video>
                    <div class="clip-controls">
                        <button class="btn-clip-play" onclick="videoDisplay.playClip('${clipId}', ${clip.start_time}, ${clip.end_time})">
                            <span class="material-icons">play_arrow</span>
                            この区間を再生
                        </button>
                    </div>
                </div>
            `;
        });

        clipsGrid.innerHTML = clipsHtml;
        
        // Setup HLS for each clip video after DOM insertion
        clips.forEach((clip, index) => {
            const clipId = `video-clip-${index}`;
            const videoElement = document.getElementById(clipId);
            if (videoElement) {
                const videoUrl = clip.video_uri || sourceVideoUrl;
                this._setupVideoPlayer(videoElement, videoUrl);
            }
        });
        
        clipsSection.style.display = 'block';

        // Setup clip playback handlers
        this.setupClipHandlers();
    }

    /**
     * Setup event handlers for video clips
     */
    setupClipHandlers() {
        document.querySelectorAll('.clip-video').forEach(video => {
            const startTime = parseFloat(video.dataset.start);
            const endTime = parseFloat(video.dataset.end);

            // Set initial time to start
            video.currentTime = startTime;

            // Monitor playback and loop within range
            video.addEventListener('timeupdate', function() {
                if (this.currentTime >= endTime) {
                    this.pause();
                    this.currentTime = startTime;
                }
            });

            // Reset to start when seeking outside range
            video.addEventListener('seeked', function() {
                if (this.currentTime < startTime || this.currentTime >= endTime) {
                    this.currentTime = startTime;
                }
            });
        });
    }

    /**
     * Play a specific video clip
     * @param {string} clipId - ID of the video element
     * @param {number} startTime - Start time in seconds
     * @param {number} endTime - End time in seconds
     */
    playClip(clipId, startTime, endTime) {
        const video = document.getElementById(clipId);
        if (!video) {
            console.error('Video element not found:', clipId);
            return;
        }

        video.currentTime = startTime;
        video.play().catch(err => {
            console.error('Failed to play video clip:', err);
        });
    }

    /**
     * Format seconds to MM:SS
     * @param {number} seconds - Time in seconds
     * @returns {string} Formatted time string
     */
    formatTime(seconds) {
        if (!seconds && seconds !== 0) return '00:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

// Create global instance
const videoDisplay = new VideoDisplay();
