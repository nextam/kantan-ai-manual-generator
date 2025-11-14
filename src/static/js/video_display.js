/**
 * File: video_display.js
 * Purpose: Video display and clip playback functionality for manual detail page
 * Main functionality: Display source videos, support video clip playback with time ranges
 * Dependencies: None (vanilla JavaScript)
 */

class VideoDisplay {
    constructor() {
        this.videoSection = null;
        this.videoGrid = null;
        this.currentManual = null;
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

            videosHtml += `
                <div class="video-item">
                    ${hideNoviceLabel ? '' : `<div class="video-label ${labelClass}">${labelText}</div>`}
                    <video controls id="source-video-${video.file_id}" data-video-id="${video.file_id}">
                        <source src="${video.url}" type="video/mp4">
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
