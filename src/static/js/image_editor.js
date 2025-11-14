/**
 * File: image_editor.js
 * Purpose: Image rotation and editing functionality for extracted images
 * Main functionality: Rotate images, save rotation state, update manual display
 * Dependencies: None (vanilla JavaScript)
 */

class ImageEditor {
    constructor() {
        this.currentManual = null;
        this.extractedImages = [];
        this.rotationStates = {}; // stepNumber -> rotation angle
    }

    /**
     * Initialize image editor for a manual
     * @param {Object} manual - Manual object with extracted_images
     */
    init(manual) {
        this.currentManual = manual;
        this.extractedImages = manual.extracted_images || [];
        this.rotationStates = {};

        console.log('Image editor initialized:', {
            imageCount: this.extractedImages.length,
            manual: manual
        });

        // Add rotation controls to images
        this.addRotationControls();
    }

    /**
     * Add rotation controls to all images in the manual
     */
    addRotationControls() {
        // Wait for DOM to be ready
        requestAnimationFrame(() => {
            const figures = document.querySelectorAll('figure[data-step]');
            console.log(`Found ${figures.length} figure elements with data-step`);

            figures.forEach((figure, index) => {
                const stepNumber = parseInt(figure.getAttribute('data-step'));
                const img = figure.querySelector('img');

                if (!img) {
                    console.warn(`No img found in figure ${index}`);
                    return;
                }

                // Remove existing controls
                const existingControls = figure.querySelector('.image-rotate-controls');
                if (existingControls) {
                    existingControls.remove();
                }

                // Create rotation control buttons
                const controlsDiv = document.createElement('div');
                controlsDiv.className = 'image-rotate-controls';
                controlsDiv.innerHTML = `
                    <button class="btn-rotate-left" title="左に90度回転" data-step="${stepNumber}">
                        <span class="material-icons">rotate_left</span>
                    </button>
                    <button class="btn-rotate-right" title="右に90度回転" data-step="${stepNumber}">
                        <span class="material-icons">rotate_right</span>
                    </button>
                `;

                // Add event listeners
                controlsDiv.querySelector('.btn-rotate-left').addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.rotateImage(stepNumber, -90);
                });

                controlsDiv.querySelector('.btn-rotate-right').addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.rotateImage(stepNumber, 90);
                });

                // Make figure relative for absolute positioning of controls
                figure.style.position = 'relative';
                figure.appendChild(controlsDiv);

                console.log(`Added rotation controls for step ${stepNumber}`);
            });
        });
    }

    /**
     * Rotate an image by a given angle
     * @param {number} stepNumber - Step number of the image
     * @param {number} delta - Rotation angle change (-90 or 90)
     */
    async rotateImage(stepNumber, delta) {
        console.log('Rotating image:', { stepNumber, delta });

        // Get current rotation
        const currentRotation = this.rotationStates[stepNumber] || 0;
        let newRotation = (currentRotation + delta) % 360;
        if (newRotation < 0) newRotation += 360;

        // Normalize to 0, 90, 180, 270
        const allowed = [0, 90, 180, 270];
        newRotation = allowed.reduce((prev, curr) => 
            Math.abs(curr - newRotation) < Math.abs(prev - newRotation) ? curr : prev, 0
        );

        console.log('Rotation angles:', { current: currentRotation, delta, new: newRotation });

        // Update local state
        this.rotationStates[stepNumber] = newRotation;

        // Apply rotation visually
        this.applyRotationToImage(stepNumber, newRotation);

        // Save to server
        try {
            await this.saveRotationToServer(stepNumber, newRotation);
            console.log('Rotation saved successfully');
        } catch (error) {
            console.error('Failed to save rotation:', error);
            alert('画像の回転を保存できませんでした: ' + error.message);
            // Revert rotation on failure
            this.rotationStates[stepNumber] = currentRotation;
            this.applyRotationToImage(stepNumber, currentRotation);
        }
    }

    /**
     * Apply rotation CSS to an image element
     * @param {number} stepNumber - Step number
     * @param {number} rotation - Rotation angle in degrees
     */
    applyRotationToImage(stepNumber, rotation) {
        const figure = document.querySelector(`figure[data-step="${stepNumber}"]`);
        if (!figure) {
            console.error('Figure not found for step:', stepNumber);
            return;
        }

        const img = figure.querySelector('img');
        if (!img) {
            console.error('Image not found in figure for step:', stepNumber);
            return;
        }

        img.style.transform = `rotate(${rotation}deg)`;
        img.style.transition = 'transform 0.3s ease';

        console.log(`Applied rotation ${rotation}deg to step ${stepNumber}`);
    }

    /**
     * Save rotation state to server
     * @param {number} stepNumber - Step number
     * @param {number} rotation - Rotation angle
     */
    async saveRotationToServer(stepNumber, rotation) {
        if (!this.currentManual || !this.currentManual.id) {
            throw new Error('マニュアルが読み込まれていません');
        }

        const payload = {
            manual_id: this.currentManual.id,
            step_number: stepNumber,
            rotation: rotation
        };

        console.log('Saving rotation to server:', payload);

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        try {
            const response = await fetch('/api/manuals/image/rotate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || '回転の保存に失敗しました');
            }

            return data;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('リクエストがタイムアウトしました。ネットワーク接続を確認してください。');
            }
            throw error;
        }
    }

    /**
     * Load rotation states from extracted images
     */
    loadRotationStates() {
        this.extractedImages.forEach(img => {
            if (img.rotation !== undefined && img.step_number !== undefined) {
                this.rotationStates[img.step_number] = img.rotation;
                this.applyRotationToImage(img.step_number, img.rotation);
            }
        });

        console.log('Loaded rotation states:', this.rotationStates);
    }
}

// Create global instance
const imageEditor = new ImageEditor();
