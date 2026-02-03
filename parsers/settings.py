#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings/Configuration for YouTube Parser"""

# API Configuration
API_KEY = "AIzaSyAIJzVRs26WXax6t7f8jOKMjfT8BMuKjek"

# Parsing Settings
MAX_RESULTS = 0  # 0 = all comments, N = max N comments
SORT_ORDER = "relevance"  # "relevance" | "time" | "rating"
REQUEST_DELAY = 0.1  # Delay between API requests
MAX_RETRIES = 3

# Data Collection
COLLECT_VIDEO_STATS = True
COLLECT_AUTHOR_INFO = True
COLLECT_COMMENT_LIKES = True
COLLECT_REPLIES = True

# Output Settings
OUTPUT_FORMAT = "enriched_txt"  # "txt" | "enriched_txt" | "both"
ENCODING = "utf-8"

# Logging
LOGGING = True
LOG_LEVEL = "INFO"

# Paths
RESULTS_DIR = "results"
URLS_FILE = "urls.txt"

# API Limits
MAX_COMMENTS_PER_REQUEST = 100  # YouTube API limit
MAX_API_REQUESTS_PER_DAY = 10000  # Free account limit
