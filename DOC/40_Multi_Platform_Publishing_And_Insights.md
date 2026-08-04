# 40 - Multi-Platform Publishing and Insights

## Supported Adapter Flows

### YouTube

1. Start a resumable `videos.insert` session.
2. Upload the approved MP4 to the trusted Google upload URL.
3. Set privacy to private first.
4. Include scheduled time when supplied.
5. Include synthetic-media disclosure.
6. Store the returned video ID.

Official references:

- https://developers.google.com/youtube/v3/docs/videos/insert
- https://developers.google.com/youtube/v3/guides/uploading_a_video
- https://developers.google.com/youtube/analytics/reference/reports/query

Unverified API projects can be restricted to private uploads until Google audit requirements are
satisfied.

### Instagram

1. Require a public HTTPS video URL.
2. Create a REELS media container.
3. check the container status.
4. Publish only after `FINISHED`.
5. Store the returned media ID.

Instagram publishing requires a professional account and the applicable Meta login,
permissions, and app-review state.

### Facebook

1. Start a Page Reel upload session.
2. Validate the returned upload host.
3. Send the local MP4 with its exact byte length.
4. Finish with `video_state=PUBLISHED`.
5. Store the video ID.

### X

1. Initialize a `tweet_video` media upload.
2. Upload bounded chunks.
3. Finalize media processing.
4. Create the post with the media ID.
5. Include AI-media disclosure.
6. Store the post ID.

Official references:

- https://docs.x.com/x-api/media/initialize-media-upload
- https://docs.x.com/x-api/media/append-media-upload
- https://docs.x.com/x-api/media/finalize-media-upload
- https://docs.x.com/x-api/posts/create-post

## Common Publish Gate

Every platform requires:

- a real MP4 container;
- narration audio;
- matching approved artifact SHA-256;
- medical-review ID;
- separate publish-approval ID;
- non-empty title and caption.

## Idempotency and Retry Safety

A persistent unique job exists for each candidate, platform, and approved artifact hash.

- Concurrent workers cannot claim the same publication twice.
- Published jobs do not call a platform again.
- Processing-pending and transient responses become retryable jobs.
- Permanent API errors fail closed.
- Retry attempts are bounded.
- Tokens and raw platform error bodies are not persisted.

## Insight Normalization

YouTube, Instagram, Facebook, and X metrics are converted into:

- impressions;
- views;
- average watch ratio;
- likes;
- comments;
- shares;
- available-metric names.

This normalized record feeds the online-learning reward function. Missing metrics remain
explicitly absent or zero; the system does not manufacture performance.

## Live Boundary

No real platform request has been executed. Live operation still requires operator-owned OAuth
credentials, account IDs, platform/app approval, quotas, and a production-ready media file.

