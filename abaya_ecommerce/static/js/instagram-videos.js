// Add this to static/js/instagram-videos.js

// Track current page
let currentPage = 1;

function loadMoreVideos() {
    const btn = document.getElementById('load-more-videos');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    btn.disabled = true;

    // Fetch more videos via AJAX
    fetch(`/api/instagram/videos/?page=${currentPage + 1}&count=4`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.videos.length > 0) {
                    // Increment page
                    currentPage++;

                    // Add videos to the page
                    const videosContainer = document.querySelector('.instagram-videos-container');

                    data.videos.forEach(video => {
                        const videoElement = createVideoElement(video);
                        videosContainer.appendChild(videoElement);
                    });

                    // Initialize click events for new videos
                    initializeVideoClicks();

                    // Hide the button if no more videos
                    if (!data.has_more) {
                        btn.style.display = 'none';
                    }
                } else {
                    btn.style.display = 'none';
                    showNotification('No more videos to load', 'info');
                }
            } else {
                showNotification('Failed to load more videos', 'danger');
            }
        })
        .catch(error => {
            console.error('Error loading more videos:', error);
            showNotification('An error occurred while loading videos', 'danger');
        })
        .finally(() => {
            // Reset button
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

function createVideoElement(video) {
    // Format date
    const date = new Date(video.timestamp);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Create element
    const col = document.createElement('div');
    col.className = 'col-lg-3 col-md-6 col-sm-6';

    col.innerHTML = `
        <div class="instagram-video-item card h-100 border-0 shadow-sm overflow-hidden">
            <div class="position-relative">
                ${video.thumbnail_url
            ? `<img src="${video.thumbnail_url}" alt="Instagram Video" class="card-img-top instagram-thumbnail">`
            : video.media_url
                ? `<img src="${video.media_url}" alt="Instagram Video" class="card-img-top instagram-thumbnail">`
                : `<div class="instagram-placeholder d-flex align-items-center justify-content-center bg-light" style="height: 300px;">
                            <i class="fab fa-instagram fa-3x text-primary"></i>
                           </div>`
        }
                
                <div class="instagram-play-button">
                    <a href="${video.permalink}" target="_blank" class="btn-play">
                        <i class="fas fa-play"></i>
                    </a>
                </div>
            </div>
            
            <div class="card-body">
                <p class="card-text instagram-caption text-truncate">
                    ${video.caption || "Watch on Instagram"}
                </p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        ${formattedDate}
                    </small>
                    <a href="${video.permalink}" target="_blank" class="btn btn-sm btn-outline-primary">
                        View on Instagram
                    </a>
                </div>
            </div>
        </div>
    `;

    return col;
}

function initializeVideoClicks() {
    // Handle video clicks for all videos including newly added ones
    const videoItems = document.querySelectorAll('.instagram-video-item');

    videoItems.forEach(item => {
        // Skip if already initialized
        if (item.dataset.initialized) return;

        const playButton = item.querySelector('.btn-play');
        const permalink = playButton ? playButton.closest('a').getAttribute('href') : null;

        item.addEventListener('click', function (e) {
            // Don't trigger if clicking on the "View on Instagram" button
            if (e.target.closest('.btn-outline-primary')) {
                return;
            }

            // Otherwise open the Instagram link
            if (permalink) {
                window.open(permalink, '_blank');
            }
        });

        // Mark as initialized
        item.dataset.initialized = 'true';
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeVideoClicks();

    // Set up load more button
    const loadMoreBtn = document.getElementById('load-more-videos');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', loadMoreVideos);
    }
});