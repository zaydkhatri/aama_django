# core/instagram_service.py
import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class InstagramService:
    """Service for fetching content from Instagram"""
    
    CACHE_KEY = 'instagram_feed'
    CACHE_TIMEOUT = 60 * 60  # 1 hour
    
    @staticmethod
    def get_instagram_feed(count=8, media_type=None):
        """
        Get Instagram feed with photos and videos
        
        Args:
            count: Number of items to return
            media_type: Filter by media type ('IMAGE', 'VIDEO', 'CAROUSEL_ALBUM', None for all)
        
        Returns:
            List of Instagram media items with fields:
            - id: Media ID
            - media_type: 'IMAGE', 'VIDEO', or 'CAROUSEL_ALBUM'
            - media_url: URL of the media
            - permalink: Link to the Instagram post
            - thumbnail_url: Thumbnail for videos (None for images)
            - caption: Post caption
            - timestamp: When the media was posted
        """
        # Check cache first
        cache_key = f"{InstagramService.CACHE_KEY}_{count}_{media_type}"
        cached_feed = cache.get(cache_key)
        if cached_feed:
            return cached_feed
            
        try:
            # Instagram Graph API endpoint
            base_url = "https://graph.instagram.com/me/media"
            
            # API parameters
            params = {
                'fields': 'id,media_type,media_url,permalink,thumbnail_url,caption,timestamp',
                'access_token': settings.INSTAGRAM_ACCESS_TOKEN,
                'limit': count * 2  # Request more to account for filtering
            }
            
            # Make the API request
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse response
            data = response.json()
            media_items = data.get('data', [])
            
            # Filter by media type if specified
            if media_type:
                media_items = [item for item in media_items if item.get('media_type') == media_type]
            
            # Limit to requested count
            media_items = media_items[:count]
            
            # Cache the result
            cache.set(cache_key, media_items, InstagramService.CACHE_TIMEOUT)
            
            return media_items
            
        except Exception as e:
            logger.error(f"Error fetching Instagram feed: {str(e)}")
            return []
    
    @staticmethod
    def get_instagram_videos(count=4):
        """Get Instagram videos only"""
        return InstagramService.get_instagram_feed(count=count, media_type='VIDEO')