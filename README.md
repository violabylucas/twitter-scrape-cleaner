# twitter-scrape-cleaner

## Python cleans NDJSON file

### Cleans for:
- "bookmark_count"
- "collected_at"
- "conversation_id"
- "favourites_count"
- "followers_count"
- "following_count"
- "in_reply_to_screen_name"
- "in_reply_to_user_id"
- "is_quote_status"
- "last_updated_at"
- "like_count"
- "listed_count"
- "media_count"
- "quote_count"
- "reply_count"
- "retweet_count"
- "screen_name"
- "search_url"
- "source_platform"
- "source_url"
- "statuses_count"
- "tweet_created_at"
- "tweet_id"
- "tweet_lang"
- "tweet_text"
- "user_description"
- "user_description_lang"
- "user_id"
- "user_location"
- "user_name"
- "view_count"

### Notes:
    Top-level wrapper fields are preserved only where useful for provenance and timestamps.
    Tweet and user content are extracted from raw['data'].
    Media fields are excluded by omission.
    User interaction / relationship fields are excluded by omission.
