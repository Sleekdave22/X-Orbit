# Orbit Market integration

Source: Sleekdave22/X-orbitupdate, `orbit-market`, commit `55ab5e6c010749a79941973bbbb47bb682aadbaf`.

The shared browser preview previously served `main`, which had no Market entry, while the live X-Orbit backend also lacked the Market module. The preview checkout now uses `orbit-market`. Its Market assets and API requests use the same authoritative X-Orbit backend as chat and Orbit Play. No second database is introduced for Market.

The selected X-Orbit source retains its current theme, account, notification, local attachment and chat-position fixes. It gains a home entry beside Orbit Play and an authenticated Market page. Android version 25 adds the same entry without replacing the app or its account. Market opens through the existing same-origin WebView; its seller-chat bridge verifies the seller profile through the authenticated backend before opening a conversation.

## Features and contracts

- Browse active text adverts and filter categories; search returns matching shops/accounts.
- One shop per account with a unique shop name, shop details and editable own adverts.
- Post, remove and renew adverts; 30-day lifetime, 20 live/held adverts per shop and five new adverts per hour.
- Report adverts; three distinct reports hold an advert for administrator review. Existing backend administrator permissions control restore/removal.
- Message seller uses the existing contact endpoint and opens the selected seller's chat. Existing block checks remain enforced.
- GET `/market/summary`, `/market/ads`, `/market/account`; authenticated POST `/market/register`, `/market/update_shop`, `/market/post_ad`, `/market/remove_ad`, `/market/renew_ad`, `/market/report`, `/market/admin_restore`, `/market/admin_remove`.

The additive migration creates `market_accounts`, `market_ads`, `market_reports` and their indexes. It does not rewrite existing accounts, chats, gaming identities, rankings, wallet records or sessions. Prices are advert text: this feature does not collect payments or enable real-money wallet actions.

## Validation

Eight temporary-database integration tests cover authentication, shop ownership/uniqueness, shared advert visibility/search, expiry/rate limits/removal, reports and administrator permissions, seller contact, blocked seller contact and repeated additive initialization preserving existing accounts/messages/adverts. All pass.

All 24 existing browser JavaScript regression scripts plus the Market UI script pass. The Market script checks syntax, the home-only entry, web/native seller routing, blocked contacts and account-switch handling. Android debug assembly and all 16 chat JVM tests pass, including Market static-asset separation from live API calls. Physical-phone Market navigation and live-browser checks follow backend deployment; the automated results do not claim those checks.

## Verification after deployment

Refresh the browser home and sign in. Market appears beside Orbit Play. Open Browse and My shop; no test shop or advert should have been created in live data by the automated tests. Check the same home entry on the updated S21. Open a real seller's Message seller action only when intending to connect; it should open that seller's authorized conversation.
