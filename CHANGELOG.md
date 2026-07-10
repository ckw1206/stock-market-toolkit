# Changelog

## [0.20.0](https://github.com/ckw1206/stock-market-toolkit/compare/v0.19.0...v0.20.0) (2026-07-10)


### Features

* support multiple Discord webhook channels for alert notifications ([#324](https://github.com/ckw1206/stock-market-toolkit/issues/324)) ([a00a9db](https://github.com/ckw1206/stock-market-toolkit/commit/a00a9db2816ea6144f4a64f49963966f88d83130))


### Bug Fixes

* **dashboard:** scope card scrollbars to content, matching HistoryTable ([#321](https://github.com/ckw1206/stock-market-toolkit/issues/321)) ([ba39178](https://github.com/ckw1206/stock-market-toolkit/commit/ba391789473e739da35009e3bae8d287fad6572a))
* redirect to login on session expiry instead of showing raw error ([#323](https://github.com/ckw1206/stock-market-toolkit/issues/323)) ([c0fe1d5](https://github.com/ckw1206/stock-market-toolkit/commit/c0fe1d53f7969f95a7d5aafee69ddc7906608884))
* **signals:** ignore empty scans when selecting latest top signals ([#320](https://github.com/ckw1206/stock-market-toolkit/issues/320)) ([ff177a2](https://github.com/ckw1206/stock-market-toolkit/commit/ff177a27af6a5dd37cddbf361a5f0c5bbd508e52))

## [0.19.0](https://github.com/ckw1206/stock-market-toolkit/compare/v0.18.0...v0.19.0) (2026-07-09)


### Features

* preload watchlist ticker data at login and reuse it across pages ([#317](https://github.com/ckw1206/stock-market-toolkit/issues/317)) ([04c1435](https://github.com/ckw1206/stock-market-toolkit/commit/04c14351701cb6aef09aa2b5eaee3d0b3b6397fa))


### Bug Fixes

* actually schedule the alert check — alerts never fired ([#316](https://github.com/ckw1206/stock-market-toolkit/issues/316)) ([b3f669d](https://github.com/ckw1206/stock-market-toolkit/commit/b3f669dd46d57ed5dd980c3a728ef2ab321fadb8))
* drop NaN-Close rows in the provider chain — they 500 whole responses ([#319](https://github.com/ckw1206/stock-market-toolkit/issues/319)) ([b188677](https://github.com/ckw1206/stock-market-toolkit/commit/b188677fc49bd0ca4ac5784916231a425ed7791a))
* stop pinning a DB connection for the whole request in get_current_user ([#315](https://github.com/ckw1206/stock-market-toolkit/issues/315)) ([3ef6f85](https://github.com/ckw1206/stock-market-toolkit/commit/3ef6f854a4a4a21f846263587be8205346d467e5))

## [0.18.0](https://github.com/ckw1206/stock-market-toolkit/compare/v0.17.1...v0.18.0) (2026-07-09)


### Features

* dashboard overview layout ([#312](https://github.com/ckw1206/stock-market-toolkit/issues/312)) ([0eebbcf](https://github.com/ckw1206/stock-market-toolkit/commit/0eebbcf35482c60a24a258a1133ca220523aab7e))

## [0.17.1](https://github.com/ckw1206/stock-market-toolkit/compare/v0.17.0...v0.17.1) (2026-07-06)


### Bug Fixes

* remove icon prefixes from Screener & Portfolio page titles ([#308](https://github.com/ckw1206/stock-market-toolkit/issues/308)) ([c19a390](https://github.com/ckw1206/stock-market-toolkit/commit/c19a3904536625f9a390b8f535500588c8188a5b))

## [0.17.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.16.0...v0.17.0) (2026-07-06)


### Features

* **dashboard:** persist last-viewed ticker in localStorage ([#290](https://github.com/ai-workflow-space/stock-market-toolkit/issues/290)) ([1810627](https://github.com/ai-workflow-space/stock-market-toolkit/commit/1810627921ae17ff03874d1d2b12e74d7c437a86))
* **paper-trading:** [#297](https://github.com/ai-workflow-space/stock-market-toolkit/issues/297) — starting_cash, backdated trades, undo, reset ([#301](https://github.com/ai-workflow-space/stock-market-toolkit/issues/301)) ([4a4fb9f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4a4fb9f96196f4751e7b54a1b4405b6b028b00c1))
* **signals:** port NoteField, TagEditor, sort toggle, tag filter from WatchlistPage ([#302](https://github.com/ai-workflow-space/stock-market-toolkit/issues/302)) ([629c4e2](https://github.com/ai-workflow-space/stock-market-toolkit/commit/629c4e295146e2778d4b0659d296bb56882adb09))


### Bug Fixes

* **#299:** Pad get_history lookback for indicator computations ([#303](https://github.com/ai-workflow-space/stock-market-toolkit/issues/303)) ([fb7c207](https://github.com/ai-workflow-space/stock-market-toolkit/commit/fb7c20783f4fcac5e5408275c73e13647f23ad36))
* 283: run nightly signal scan in-process instead of external cron ([#296](https://github.com/ai-workflow-space/stock-market-toolkit/issues/296)) ([2021f37](https://github.com/ai-workflow-space/stock-market-toolkit/commit/2021f377915692ccda4680d038e902d489352fc8))
* **HistoryTable:** remove hardcoded 30-row cap ([#304](https://github.com/ai-workflow-space/stock-market-toolkit/issues/304)) ([6b01d6d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6b01d6d2aa51f8f7196f33cb2e88ca4eb8623027))
* **SignalCard:** split header into two rows to prevent badge overflow ([#284](https://github.com/ai-workflow-space/stock-market-toolkit/issues/284)) ([07f68c6](https://github.com/ai-workflow-space/stock-market-toolkit/commit/07f68c6ae9307842cd829527a775cf1dd4687851))

## [0.16.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.15.0...v0.16.0) (2026-07-05)


### Features

* alert snooze + quiet hours with catch-up digest ([#274](https://github.com/ai-workflow-space/stock-market-toolkit/issues/274)) ([4c5a87e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4c5a87eabc6dc171b6842280ead327fb6e542578))
* CSV export for Screener results and triggered-alert history ([#276](https://github.com/ai-workflow-space/stock-market-toolkit/issues/276)) ([d4fa3b3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d4fa3b3450275b71f54b5e0cc464bdf49e64ebb6))
* market breadth widget ([#272](https://github.com/ai-workflow-space/stock-market-toolkit/issues/272)) ([8324db9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8324db95751a470f957f656922cf6e5e177b3a01))
* market breadth widget ([#272](https://github.com/ai-workflow-space/stock-market-toolkit/issues/272)) ([8324db9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8324db95751a470f957f656922cf6e5e177b3a01))
* paper-trading portfolio ([#273](https://github.com/ai-workflow-space/stock-market-toolkit/issues/273)) ([3f6762e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/3f6762e71b18040d33454c112f489c884ecb2c98))
* watchlist notes, tags, and tag filtering ([#275](https://github.com/ai-workflow-space/stock-market-toolkit/issues/275)) ([8f23c9f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8f23c9f18b08452abc860df5aa9e8d92d905f29d))

## [0.15.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.14.0...v0.15.0) (2026-07-04)


### Features

* ATR-based position-size and stop-loss calculator ([d048573](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d04857370a060210ee8ef27ace17c8147855a5ce))
* ATR-based position-size and stop-loss calculator ([#267](https://github.com/ai-workflow-space/stock-market-toolkit/issues/267)) ([d048573](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d04857370a060210ee8ef27ace17c8147855a5ce))
* earnings-date awareness ([#270](https://github.com/ai-workflow-space/stock-market-toolkit/issues/270)) ([d1caaa8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d1caaa81aab030259eb98b6dee5ce1713154792c))
* earnings-date awareness ([#270](https://github.com/ai-workflow-space/stock-market-toolkit/issues/270)) ([d1caaa8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d1caaa81aab030259eb98b6dee5ce1713154792c))
* multi-timeframe confluence (weekly trend confirmation) ([dccfa5f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/dccfa5f65dec8d117058f9d273ab5e65a6db3bd1))
* multi-timeframe confluence (weekly trend confirmation) ([#268](https://github.com/ai-workflow-space/stock-market-toolkit/issues/268)) ([dccfa5f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/dccfa5f65dec8d117058f9d273ab5e65a6db3bd1))
* RSI/MACD divergence detection ([b4e3bf4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b4e3bf46bf94391bfaa2667a7a5f52fa3a9165d5))
* RSI/MACD divergence detection ([#269](https://github.com/ai-workflow-space/stock-market-toolkit/issues/269)) ([b4e3bf4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b4e3bf46bf94391bfaa2667a7a5f52fa3a9165d5))

## [0.14.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.13.0...v0.14.0) (2026-07-03)


### Features

* add advanced signal analysis, nightly scanning, backtesting, and screener ([e69c010](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e69c0104a99a2d3a7e597cc8d4dfd513c7a55641))
* daily Top Signals feed with nightly market scan ([#252](https://github.com/ai-workflow-space/stock-market-toolkit/issues/252)) ([61b3c97](https://github.com/ai-workflow-space/stock-market-toolkit/commit/61b3c972539adf34d03cfa637b8d1a1fe4a583c0))
* RVOL spike + 52-week breakout signals, signal/rvol alert metrics ([b8a5a1b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b8a5a1b17f111d41beacd35fe45bc82a88befb74))
* RVOL spike + 52-week breakout signals, signal/rvol alert metrics ([#251](https://github.com/ai-workflow-space/stock-market-toolkit/issues/251)) ([b8a5a1b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b8a5a1b17f111d41beacd35fe45bc82a88befb74))
* screener and sector heatmap over nightly scan results ([#254](https://github.com/ai-workflow-space/stock-market-toolkit/issues/254)) ([e69c010](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e69c0104a99a2d3a7e597cc8d4dfd513c7a55641))
* signal backtest with historical hit rate and average return ([#253](https://github.com/ai-workflow-space/stock-market-toolkit/issues/253)) ([b1dd152](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b1dd15216462cddf4fbbc7623faa5d9068c1c226))

## [0.13.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.12.0...v0.13.0) (2026-07-03)


### Features

* market-hours-aware global gate in check_alerts() ([#243](https://github.com/ai-workflow-space/stock-market-toolkit/issues/243)) ([738b92d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/738b92d00e85d3ad22a427a7ca0c06f40d074749))
* market-hours-aware global gate in check_alerts() ([#243](https://github.com/ai-workflow-space/stock-market-toolkit/issues/243)) ([738b92d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/738b92d00e85d3ad22a427a7ca0c06f40d074749))


### Bug Fixes

* native select dark mode + timezone dropdown ([bcef833](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bcef83338dda5aafd96cac61237a98b75c8f2383))
* native select dark mode + timezone dropdown [#248](https://github.com/ai-workflow-space/stock-market-toolkit/issues/248) ([bcef833](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bcef83338dda5aafd96cac61237a98b75c8f2383))
* surface batch-fetch errors with error banner and toast ([09c82cf](https://github.com/ai-workflow-space/stock-market-toolkit/commit/09c82cf5b5fd31fb58fc47965a9ce8a4d9464f29))

## [0.12.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.11.0...v0.12.0) (2026-07-01)


### Features

* **alerts:** add email_subject/email_body template fields to NotificationSettings ([#235](https://github.com/ai-workflow-space/stock-market-toolkit/issues/235)) ([fd930df](https://github.com/ai-workflow-space/stock-market-toolkit/commit/fd930df44e6ee2062598dc7204c0c5d06e15ed53))
* **alerts:** extend AlertUpdate + update_alert for full alert editing ([#242](https://github.com/ai-workflow-space/stock-market-toolkit/issues/242)) ([#245](https://github.com/ai-workflow-space/stock-market-toolkit/issues/245)) ([e548b4e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e548b4ec481feef743a9215b9a73958b6b2df133))
* **alerts:** per-user SMTP settings ([#239](https://github.com/ai-workflow-space/stock-market-toolkit/issues/239)) ([db5bbaf](https://github.com/ai-workflow-space/stock-market-toolkit/commit/db5bbafd000550b5a181d6d0b71f3154b5fef7e6))
* **i18n:** add full Traditional Chinese (zh-TW) localization ([903cfb9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/903cfb93ca81717c0ce7fa3538cb211934a690bc))
* language menu in navbar with 繁體中文 (i18n) ([#206](https://github.com/ai-workflow-space/stock-market-toolkit/issues/206)) ([903cfb9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/903cfb93ca81717c0ce7fa3538cb211934a690bc))


### Bug Fixes

* **i18n:** address review findings and CI issues ([903cfb9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/903cfb93ca81717c0ce7fa3538cb211934a690bc))

## [0.11.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.10.0...v0.11.0) (2026-07-01)


### Features

* **alerts:** customizable email subject/body templates ([#228](https://github.com/ai-workflow-space/stock-market-toolkit/issues/228)) ([771c6c8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/771c6c868df468ba8cd7bd6a572b67afd8059d4c))
* extract cron endpoints from main.py into routes/cron.py ([#220](https://github.com/ai-workflow-space/stock-market-toolkit/issues/220)) ([916884e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/916884e5749e01273459d3e62ac0fb6570c34e5d))
* split routes/stocks.py into 4 focused route modules ([#224](https://github.com/ai-workflow-space/stock-market-toolkit/issues/224)) ([#225](https://github.com/ai-workflow-space/stock-market-toolkit/issues/225)) ([8ce8097](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8ce8097ae7790359629be5f7d75470dfcb89780f))


### Bug Fixes

* **compose:** honest version/commit in feat-test + make target to inject real values ([#229](https://github.com/ai-workflow-space/stock-market-toolkit/issues/229)) ([bddb637](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bddb637d755b99337ec14504f2d1db071d473f79))
* keep alembic multi-head fix when reverting select change ([036b539](https://github.com/ai-workflow-space/stock-market-toolkit/commit/036b5396da5d3d98e0ee3c6579586905ec95d497))
* Replace native select with Radix Select in CreateAlertDialog ([0877ca6](https://github.com/ai-workflow-space/stock-market-toolkit/commit/0877ca69a5bf751c9161141a783c45f94b628913))
* Replace native select with Radix Select in CreateAlertDialog (stock-market-toolkit[#230](https://github.com/ai-workflow-space/stock-market-toolkit/issues/230)) ([c9ec98e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/c9ec98e973d6e38b600abfc4fb946e5387fd289c))
* use 'heads' (plural) in alembic command.upgrade to handle multi-head migration trees ([#232](https://github.com/ai-workflow-space/stock-market-toolkit/issues/232)) ([b2cd0a0](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b2cd0a031cacaf1c635a34f326c81ca83bfb6051))

## [0.10.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.7...v0.10.0) (2026-06-28)


### Features

* **alerts:** Send test button for Discord webhook ([#198](https://github.com/ai-workflow-space/stock-market-toolkit/issues/198)) ([98bcb25](https://github.com/ai-workflow-space/stock-market-toolkit/commit/98bcb25d3f79cf517e44b79efd77ce8cacb567f5))


### Bug Fixes

* **analysis:** give a specific reason for recently-listed / unanalyzable symbols ([1ec932a](https://github.com/ai-workflow-space/stock-market-toolkit/commit/1ec932a9275d68412d5aa808c26566799b6c5351))
* don't let missing fundamentals/dividends break the dashboard ([#208](https://github.com/ai-workflow-space/stock-market-toolkit/issues/208)) ([7576a3e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/7576a3eafc3d18d602b8e757de18d03c35ca731a))
* read ?symbol= and ?symbols= query params in DashboardPage and ComparePage ([478355c](https://github.com/ai-workflow-space/stock-market-toolkit/commit/478355cb35cb0e933ca0f1b33944b0c4d5a48759))
* replace native select with shadcn Select for timezone dropdown (dark mode) ([#199](https://github.com/ai-workflow-space/stock-market-toolkit/issues/199)) ([44fdff4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/44fdff46b447b0fe4d5d8c6d2da1205f4b1a5009))

## [0.9.7](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.6...v0.9.7) (2026-06-27)


### Bug Fixes

* **alerts:** remove unused AlertConditionCreate import; narrow ConditionFormItem metric/operator to literal unions ([27d0bfe](https://github.com/ai-workflow-space/stock-market-toolkit/commit/27d0bfeea4b056be898d97487dad9cb5f515bb29))
* prevent dashboard 500 from dividend date handling and provider failures ([#180](https://github.com/ai-workflow-space/stock-market-toolkit/issues/180)) ([c9a3693](https://github.com/ai-workflow-space/stock-market-toolkit/commit/c9a3693c6604d87c557cf5b250cd273bf3736db2))
* Price Alert condition Value field defaults to empty, not 0 ([be44b6b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/be44b6bb2c35a3f6767b43b3aa29fc52c3642088))

## [0.9.6](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.5...v0.9.6) (2026-06-27)


### Bug Fixes

* **watchtower:** scope to containers via positional args, not --include ([aa8002d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/aa8002dc65ca4f8ab2fa352d5e62c3c3eecba479))

## [0.9.5](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.4...v0.9.5) (2026-06-27)


### Bug Fixes

* **compose:** inject version/sha/build-time into feat-test frontend build ([#175](https://github.com/ai-workflow-space/stock-market-toolkit/issues/175)) ([9d136d1](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9d136d1c335d5aeac4dd34f2c85b030221455fd1))
* **release:** wire release-please to config so version markers bump ([#174](https://github.com/ai-workflow-space/stock-market-toolkit/issues/174)) ([35822fb](https://github.com/ai-workflow-space/stock-market-toolkit/commit/35822fb54adc578cb64b27c3d5cd140b2de61b33))

## [0.9.4](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.3...v0.9.4) (2026-06-26)


### Bug Fixes

* **backend:** align tests + route with int F-score return type ([ba01c8d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/ba01c8df32f5029541bd277edb576434533811c0))

## [0.9.3](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.2...v0.9.3) (2026-06-26)


### Bug Fixes

* **frontend:** strip leading "v" from injected version so release links resolve ([2ac20cf](https://github.com/ai-workflow-space/stock-market-toolkit/commit/2ac20cfb758f450d720ba087a2761de1792c184d))

## [0.9.2](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.1...v0.9.2) (2026-06-26)


### Bug Fixes

* guard baseline index creation for idempotency (pre-Alembic adoption) ([#166](https://github.com/ai-workflow-space/stock-market-toolkit/issues/166)) ([a363e34](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a363e3424c6459950698cd742826fb89636eb461))

## [0.9.1](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.9.0...v0.9.1) (2026-06-26)


### Bug Fixes

* 4 bugs in PR [#163](https://github.com/ai-workflow-space/stock-market-toolkit/issues/163) initial_baseline migration + signals API ([#164](https://github.com/ai-workflow-space/stock-market-toolkit/issues/164)) ([21c1f43](https://github.com/ai-workflow-space/stock-market-toolkit/commit/21c1f4381c6bc1871c8a31850d3c7c936c322564))

## [0.9.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.8.0...v0.9.0) (2026-06-26)


### Features

* **DATA-6:** provider fallback chain with circuit breakers and source tagging ([#143](https://github.com/ai-workflow-space/stock-market-toolkit/issues/143)) ([11e8adb](https://github.com/ai-workflow-space/stock-market-toolkit/commit/11e8adbf73ba6aaff44327fb4512a98f58053e05))

## [0.8.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.7.0...v0.8.0) (2026-06-26)


### Features

* **BE-4:** nightly batch ingestion + score materialization ([#147](https://github.com/ai-workflow-space/stock-market-toolkit/issues/147)) ([8d61f1d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8d61f1dfb6db3b14c5959179c2f3be5df0289d2c))

## [0.7.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.6.1...v0.7.0) (2026-06-26)


### Features

* **NOTIF-2:** multi-condition alerts with AND/OR combinator ([#154](https://github.com/ai-workflow-space/stock-market-toolkit/issues/154)) ([7d1dc2d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/7d1dc2d8c18d4e02c0ea8594d415299def34c053)), closes [#115](https://github.com/ai-workflow-space/stock-market-toolkit/issues/115)

## [0.6.1](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.6.0...v0.6.1) (2026-06-26)


### Bug Fixes

* restore public derive_key alias in crypto (unbreaks test_admin_smtp on main) ([b27104d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b27104d0a448e97876a7dd66bb91d761ebc2fccc))

## [0.6.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.5.1...v0.6.0) (2026-06-26)


### Features

* adopt Alembic migrations (BE-3) ([12b72c8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/12b72c82de1c4b597762f8c0311d2a397670d5df)), closes [#105](https://github.com/ai-workflow-space/stock-market-toolkit/issues/105)
* **DATA-1:** FinMind provider for Taiwan fundamentals & dividends ([c6e17b3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/c6e17b34660c1edd89c18ce5c0e621183a63c5ef)), closes [#108](https://github.com/ai-workflow-space/stock-market-toolkit/issues/108)
* **DATA-5:** replace mock signals with real signal generation ([57bec1f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/57bec1f519d71c98afd204f4d6fe3ffa063b3208)), closes [#111](https://github.com/ai-workflow-space/stock-market-toolkit/issues/111)
* **FE-3:** merge Watchlist into Signals with view toggle ([4ea2cfb](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4ea2cfb393dcec51dec0b0414bbee1a9bc45453f)), closes [#119](https://github.com/ai-workflow-space/stock-market-toolkit/issues/119)
* **FE-4:** fundamentals & dividend dashboard cards + DATA-3/DATA-4 API ([9c9c25f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9c9c25feec0e685c84c11a219c78c1b06e710c78)), closes [#118](https://github.com/ai-workflow-space/stock-market-toolkit/issues/118)
* **NOTIF-3:** wire functional email notifications via SMTP ([4a9ea91](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4a9ea918c115b0185d5746dc602c07bdf77526af))
* notification delivery history (NOTIF-1) ([da5a035](https://github.com/ai-workflow-space/stock-market-toolkit/commit/da5a0355ba0d1e44d28b9d0dfba2e007cd24d6d5)), closes [#113](https://github.com/ai-workflow-space/stock-market-toolkit/issues/113)
* **OBS-1:** structured system logging + admin viewer ([eebcad7](https://github.com/ai-workflow-space/stock-market-toolkit/commit/eebcad7fe6c209f7a589e36ee69d043a26f69df5))
* **OBS-2:** audit log for security-relevant actions + admin viewer ([a7fca3b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a7fca3b1f445e42eab6bb7620264cb168f27d53b))
* **OBS-2:** audit log for security-relevant actions + viewer (with OBS-1 infra) ([#146](https://github.com/ai-workflow-space/stock-market-toolkit/issues/146)) ([5e69779](https://github.com/ai-workflow-space/stock-market-toolkit/commit/5e697796011f0dfc2d1158f0f5cc466333f2c7a3))
* **OBS-3:** access logs middleware + GET /api/admin/access-logs ([9bc0557](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9bc0557f00dde3e9772fb37c858979bd763b8893)), closes [#125](https://github.com/ai-workflow-space/stock-market-toolkit/issues/125)
* **OBS-4:** unified LogsPage with System/Audit/Access tabs ([0e61d40](https://github.com/ai-workflow-space/stock-market-toolkit/commit/0e61d407c97be42c8c8629230e975ef6c01f4556)), closes [#126](https://github.com/ai-workflow-space/stock-market-toolkit/issues/126)
* server-side caching + provider abstraction (BE-1, BE-2) ([ee2c021](https://github.com/ai-workflow-space/stock-market-toolkit/commit/ee2c0210ec551201a5362cc1cdc98515dc35a7e4))
* show current price & distance-to-threshold in alert dialog (FE-1) ([57e820b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/57e820b17e3b6b0875b511d05dfe5cca577c9a31)), closes [#116](https://github.com/ai-workflow-space/stock-market-toolkit/issues/116)
* show ticker name in alerts dialog and list (FE-2) ([8699392](https://github.com/ai-workflow-space/stock-market-toolkit/commit/86993929695b3d475920e39b706a83a439912b4a))
* show user registration date in admin user management table ([e85382a](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e85382ab198d442cfd7bf07b578f1682b8d90d5f))


### Bug Fixes

* **alembic:** consolidate migrations into app/alembic/versions (single head) ([9a9061f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9a9061f3d85b6a93c082abfb8189482930dda69a))
* batch signal fetches with 500ms delay between batches to avoid rate limiting ([1a67669](https://github.com/ai-workflow-space/stock-market-toolkit/commit/1a6766900c20856c298487a6e1ae6751e023ede7))
* copy alembic.ini into image + add psycopg2-binary so migrations run in container ([88aef95](https://github.com/ai-workflow-space/stock-market-toolkit/commit/88aef95d9ce9b45de149140c4c5ae4836a788272))
* correct alembic migration signature + chain; keep condition label in alerts list ([07accca](https://github.com/ai-workflow-space/stock-market-toolkit/commit/07accca35ea39e1c9340d363426b2c28eba1fa6e))
* **DATA-1:** unbreak CI — TYPE_CHECKING import + revert out-of-scope TA-lib swap ([de85c3e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/de85c3e95cb9807714d43813779a920d0f076bda))
* export market_provider singleton from app.providers; use it directly in routes ([658d8f8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/658d8f819cee669faa8b3ac81df35ac2aabb8066))
* import pandas as pd for _fs_val type hints ([05e42a9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/05e42a934ab6181374f70b6903f597e9b514991d))
* move alembic/ into app/ so COPY app/ includes it; update script_location to app/alembic ([994a521](https://github.com/ai-workflow-space/stock-market-toolkit/commit/994a52118931874ebe5bd5d085e6fc3c22bfdc24))
* **OBS-1:** disable react-hooks/set-state-in-effect for loadLogs effect ([a92a91b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a92a91bffd7b71d4939fa522adbfcd2a86d50a95))
* restore httpx to requirements.txt ([65e3d6c](https://github.com/ai-workflow-space/stock-market-toolkit/commit/65e3d6c3696c6bdeb5f8e7970d3e18d370e74034))
* restore httpx, ta, cryptography dependencies ([a2e3376](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a2e3376c42d3138aff814c81312ba974fec1d9ab))
* run Alembic in-process and fail closed on migration error ([3bd70e5](https://github.com/ai-workflow-space/stock-market-toolkit/commit/3bd70e5f5c0dfbc4106d6f2225a03b52cc334131))

## [0.5.1](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.5.0...v0.5.1) (2026-06-25)


### Bug Fixes

* include year in chart date labels to avoid ambiguity across year boundaries ([4524fe2](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4524fe2c576cf5c14f410dfb9b015d03c6a745f4))
* remove hardcoded v prefix in SettingsPage About card; APP_VERSION already includes v ([75abab0](https://github.com/ai-workflow-space/stock-market-toolkit/commit/75abab01ad98e11e635cad4ae70334c7266c8965))
* replace plain Input with SymbolSearch in Create Price Alert dialog ([9c0592a](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9c0592ab000081c25ae365db05357aaa8c4e42fa))

## [0.5.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.4.0...v0.5.0) (2026-06-25)


### Features

* add top-level React ErrorBoundary to prevent whole-app blank screens ([e5ad59e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e5ad59ee7ce0dbfe812335ae522cda4acf5b64ef))
* display release notes in Settings About card via GitHub Releases API ([15cbc7b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/15cbc7b3942f71d1d79083386eca06f5eb6c4701))
* implement [#91](https://github.com/ai-workflow-space/stock-market-toolkit/issues/91) - user menu refactor + clickable version link to GitHub release ([1036ef4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/1036ef43ea998d8575b6e5d4b0ff976f8a843db9))


### Bug Fixes

* bump version.ts fallback to 0.4.0 to match released version ([6e3460e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6e3460e738b54178571597f11574e84cf2308e0b))
* constrain and style release-notes markdown in About card ([8113279](https://github.com/ai-workflow-space/stock-market-toolkit/commit/81132799ef150435bde40d2568a71388db6ae06b))
* increase max ticker symbol length from 5 to 10 chars ([6680828](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6680828aadb3d5a933fc7e1c096cc3fae18a9c22))
* persist tracked tickers in localStorage; remove hardcoded DEFAULT_TICKERS ([#92](https://github.com/ai-workflow-space/stock-market-toolkit/issues/92)) ([4342010](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4342010d99e8a702f335bb0446365240b35b1a0e))
* persist tracked tickers to localStorage; remove hardcoded DEFAULT_TICKERS ([122ea3c](https://github.com/ai-workflow-space/stock-market-toolkit/commit/122ea3c741dc4a3bc084c60225a3ca3e751efc11))
* prevent blank Signals page from unstable watchlist symbols dependency ([c428de9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/c428de9d0d3d8255f28db482e08efb9226ff4e58))
* remove Changelog from user menu; use collapsible details for release notes ([366ad88](https://github.com/ai-workflow-space/stock-market-toolkit/commit/366ad88d3f014ed75ebcb5190af4e9a0d181af3e))
* remove dead setState before reload; gate error.message behind DEV; add EOF newline ([d2c6874](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d2c6874fa3901e6c627911e53358e64f70fb1046))
* replace in-memory trackedTickers with useWatchlist hook ([6eac8ed](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6eac8ed4e1eb2fff0980d0f811c3f75534a248dc))

## [0.4.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.3.0...v0.4.0) (2026-06-25)


### Features

* implement [#76](https://github.com/ai-workflow-space/stock-market-toolkit/issues/76) - add ticker tracking UI to Signals page ([43c6e76](https://github.com/ai-workflow-space/stock-market-toolkit/commit/43c6e768c38ea5ed033510802577caaaf23d2ae4))
* implement [#78](https://github.com/ai-workflow-space/stock-market-toolkit/issues/78) - expose WatchlistButton on Dashboard and Compare pages ([3fe82ed](https://github.com/ai-workflow-space/stock-market-toolkit/commit/3fe82ed090063d219c08857d228db97279de41ed))
* implement [#78](https://github.com/ai-workflow-space/stock-market-toolkit/issues/78) - expose WatchlistButton on Dashboard and Compare pages ([0a0357a](https://github.com/ai-workflow-space/stock-market-toolkit/commit/0a0357a54bcc98dfcc585f62cd013f33259e1890))
* implement [#79](https://github.com/ai-workflow-space/stock-market-toolkit/issues/79) - email edit and change password ([e399a05](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e399a050e940fd10f76020ce14561d55963d5b6a))
* implement [#87](https://github.com/ai-workflow-space/stock-market-toolkit/issues/87) B+C - gitattributes merge=ours for lockfiles; skip build-and-push on PR ([d3cb2f6](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d3cb2f6b4093e3cfed9a2b9f70f3af1c020c6a17))


### Bug Fixes

* actually register the merge=ours driver (was a no-op) ([bba95a3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bba95a3ffa01066c482a4885fcac5330e7e26748))
* add merge driver setup instructions to .gitattributes comments ([6c91b92](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6c91b922ad73b3b15c1af8f01c7ecfa073f26e61))
* add trailing newline to .gitattributes ([4e03830](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4e0383082fab8e14f9d658e088e6fc614e07100f))
* allow digits in ticker symbols (0050.TW international format) ([da94c78](https://github.com/ai-workflow-space/stock-market-toolkit/commit/da94c78851813e9c3e069e029e667a761b11ad36))
* bump version to 0.3.0 in backend/app/main.py ([24c4a31](https://github.com/ai-workflow-space/stock-market-toolkit/commit/24c4a3160d9fffc020383accf5c6a06c00f96cf0))
* ghost/icon buttons & inactive tabs render as blank white boxes ([ae19ac0](https://github.com/ai-workflow-space/stock-market-toolkit/commit/ae19ac0bf14df269718b48f4e5b2f4c345ac37f2))
* implement [#80](https://github.com/ai-workflow-space/stock-market-toolkit/issues/80) - dark mode button text contrast and toggle selected state ([d0a9628](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d0a962843f4493b112ca789dd482d7f5ef886c7f))
* integrate Admin/Active/Reset into Edit dialog; remove separate row toggles ([9e5b6c5](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9e5b6c56e0f60d3a89e4c4b42459b7bf3f608c0f))
* make dark-mode selected toggle actually visible (was bg-accent == border) ([01fc8d9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/01fc8d920c594be3cfa819f13681b717591d09fe))
* navbar/brand links render as raw hyperlinks (underlined blue) ([bd4c800](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bd4c8008db7955b1c2bde9a6aa9e6cd52ab97f7e))
* outline/ghost buttons, toggles & inactive tabs unreadable in dark mode ([4b79283](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4b79283d2c7c69b86c4362ef258f39b53e83a48b))
* register /watchlist route and add navbar link for WatchlistPage ([b612f16](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b612f16db74bf624689d5779bcbf9e11af9a1f42))
* resolve merge conflict markers in Navbar.tsx and SettingsPage.tsx ([63885f7](https://github.com/ai-workflow-space/stock-market-toolkit/commit/63885f7cc0515006dece439506d3f65743155989))
* use SymbolSearch combobox for Add Ticker; allow dot in tickers (BRK.B) ([f1600a3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/f1600a381805cf3d3defdb8853e2ee5fef1e0bfe))


### Documentation

* note button background reset in DESIGN_SYSTEM ([71c1d2b](https://github.com/ai-workflow-space/stock-market-toolkit/commit/71c1d2b7032689660e456c08ed1fcf24488a0377))
* record selected-state and anchor conventions in DESIGN_SYSTEM ([7780c04](https://github.com/ai-workflow-space/stock-market-toolkit/commit/7780c04d93a408c08521357fd5d2cd9d71f3f9dd))

## [0.3.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.2.0...v0.3.0) (2026-06-25)


### Features

* add /ping health-check command to CLI ([#58](https://github.com/ai-workflow-space/stock-market-toolkit/issues/58)) ([#59](https://github.com/ai-workflow-space/stock-market-toolkit/issues/59)) ([5f39962](https://github.com/ai-workflow-space/stock-market-toolkit/commit/5f39962a4ca5f5146a3e6b1d3a5fd8ee001e563a))
* add admin invite-code management UI (issue [#21](https://github.com/ai-workflow-space/stock-market-toolkit/issues/21)) ([#70](https://github.com/ai-workflow-space/stock-market-toolkit/issues/70)) ([803bb14](https://github.com/ai-workflow-space/stock-market-toolkit/commit/803bb148b95f1654edfd1f7c5004e7a63ef4f3ee))
* add reset password to user management panel (issue [#73](https://github.com/ai-workflow-space/stock-market-toolkit/issues/73)) ([b3851be](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b3851bec5cbb86c435e897f1de97fc2fff911c21))
* add user management + add user dialog (issue [#73](https://github.com/ai-workflow-space/stock-market-toolkit/issues/73)) ([85a258d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/85a258de0ff70b38162bb49743b1993bf15ad290))
* **CI:** add compose-verify job with real startup gate ([#64](https://github.com/ai-workflow-space/stock-market-toolkit/issues/64)) ([0889c7d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/0889c7dd1c21f1ffe851b90220a4fddad07c0be7))
* implement [#23](https://github.com/ai-workflow-space/stock-market-toolkit/issues/23) - adopt shadcn/ui design system and fix layout overflow ([#28](https://github.com/ai-workflow-space/stock-market-toolkit/issues/28)) ([09e998e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/09e998e25f12fa7393dbf9366bc8dc063aa41ffd))
* implement [#27](https://github.com/ai-workflow-space/stock-market-toolkit/issues/27) - favorite tickers (watchlist) ([8c52b09](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8c52b09b44e94f6ec6c8cff2c5271dfac1f324e7))
* implement [#55](https://github.com/ai-workflow-space/stock-market-toolkit/issues/55) - cache expiry timestamp in stock responses ([#56](https://github.com/ai-workflow-space/stock-market-toolkit/issues/56)) ([4f81925](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4f81925571e2f2ec3f377ce32a79348d8a74a409))
* implement [#61](https://github.com/ai-workflow-space/stock-market-toolkit/issues/61), [#62](https://github.com/ai-workflow-space/stock-market-toolkit/issues/62) - register admin router and add admin auth ([#65](https://github.com/ai-workflow-space/stock-market-toolkit/issues/65)) ([99bc2a9](https://github.com/ai-workflow-space/stock-market-toolkit/commit/99bc2a913e7ae2d9963e52837ed9d60af07e4bff))
* implement [#73](https://github.com/ai-workflow-space/stock-market-toolkit/issues/73) - first-time bootstrap & user management ([11a7f5d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/11a7f5d377bc58e8fc9d878102aed18f7064f0a1))


### Bug Fixes

* backend image crashes on boot (ImportError) — repair CI publish pipeline + add smoke test ([#71](https://github.com/ai-workflow-space/stock-market-toolkit/issues/71)) ([4ab9707](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4ab970731a1a3c92c7933b22c5a3665563f442e4))
* **CI:** create test .env before docker compose up in compose-verify job ([a1bb10f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a1bb10f5b60a129ec2a4b2ea3fff42f6b4a06180))
* correct MiniMax API URL and model name in code-review workflow ([#29](https://github.com/ai-workflow-space/stock-market-toolkit/issues/29)) ([38f6621](https://github.com/ai-workflow-space/stock-market-toolkit/commit/38f6621cd506c893c24f20be8bbcf1ccf79d0bbc))
* handle Pydantic validation errors in addUser and confirmDelete ([9eb1fdd](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9eb1fddad59930f0bfacd623104d17b0a81d4f39))
* make extractError async to properly await res.json() ([38512c7](https://github.com/ai-workflow-space/stock-market-toolkit/commit/38512c723dec5d4a26abd246c1fc1b9ad266b9b1))
* properly display Pydantic validation errors in user management (issue [#73](https://github.com/ai-workflow-space/stock-market-toolkit/issues/73)) ([900158f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/900158f0f9e9d444dcf7b491c4d2d924a5344435))
* resolve ImportError on backend boot — add InviteCode model + schemas ([#67](https://github.com/ai-workflow-space/stock-market-toolkit/issues/67), issue [#66](https://github.com/ai-workflow-space/stock-market-toolkit/issues/66)) ([8729a89](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8729a895420028df8d1f2d499e36e029db784c48))
* wire watchlist router into app to resolve backend boot ([#68](https://github.com/ai-workflow-space/stock-market-toolkit/issues/68), issue [#60](https://github.com/ai-workflow-space/stock-market-toolkit/issues/60)) ([f673dd1](https://github.com/ai-workflow-space/stock-market-toolkit/commit/f673dd1fd24525dcd2fc440d57ef65eb3f7ee4cc))

## [0.2.0](https://github.com/ai-workflow-space/stock-market-toolkit/compare/v0.1.0...v0.2.0) (2026-06-22)


### Features

* v0.2.0 release — 8 new features ([#20](https://github.com/ai-workflow-space/stock-market-toolkit/issues/20)) ([a8522bb](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a8522bba9307826efd4d0097b47d189f868ac86e))

## 0.1.0 (2026-06-22)


### Features

* add Docker publish workflow (main-only latest tag, PR preview without latest) ([dec6c1e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/dec6c1ed241450cfa4eeca0fa82e772502508869))
* add GitHub Actions CI, release-please, and Discord release notification ([b9f2b35](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b9f2b359f9a35d73d403ebee5fdd2fcb5482aa37))
* add OpenCode code review GitHub Action workflow ([e9280b4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/e9280b4744d77767fd5e41a3faa57c2b48b4414b))
* add price alert system with Discord webhook + in-app pull ([13788f8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/13788f8bffa627d926d9bb8ba4aa05a680b5fa56))
* dropdown min 3 chars + add ticker one-by-one ([53130bf](https://github.com/ai-workflow-space/stock-market-toolkit/commit/53130bf526c32560c69e3a7081816d3fd106fd14))


### Bug Fixes

* add .tabs and .tab-btn CSS for aligned Alert page tabs ([7a4b092](https://github.com/ai-workflow-space/stock-market-toolkit/commit/7a4b092f622f5c803c86cd7f870fcdfd9dc2ebc7))
* add AlertsPage CSS styling for dropdowns, modals, and cards ([75b8f2f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/75b8f2f8b3d8bc03e2389ff55d840ebd806d2dd3))
* add asyncpg for PostgreSQL in Docker ([9ef21fd](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9ef21fd4f25e13b40ba0fce9a6ddd087edb27d32))
* add key prop to Recharts Line elements to force re-render on indicator toggle ([9bed8b8](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9bed8b8c6554c0084cc8ff08052b981f33877802))
* add keys to MACD and RSI chart elements for indicator toggle ([9318de7](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9318de714163be7ff1ef1896f247e3e21efee798))
* add retry logic to yfinance search for better Taiwan/intl stock coverage ([6f4d04d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6f4d04dc81de9d148e5a6652cfbc24ed4e84e6f8))
* broken imports after useAuth hook split + dropdown 3-char gate ([9e54356](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9e54356a4c4c07cb9965b8af8203ef9f5ccf50c1))
* build Docker images for both amd64 and arm64 (M1/M2 Mac support) ([31b39c3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/31b39c3db7526bb06324a607277c15283bfdcb32))
* change frontend port 3030 → 3800 ([#11](https://github.com/ai-workflow-space/stock-market-toolkit/issues/11)) ([30bc840](https://github.com/ai-workflow-space/stock-market-toolkit/commit/30bc8407c28734fc49cfd04b76c73ed91d38c4f8))
* code-review - write output to file instead of GITHUB_OUTPUT to avoid special char issues ([dcc1487](https://github.com/ai-workflow-space/stock-market-toolkit/commit/dcc14875b9595c20408f578079e733d2465cb055))
* code-review workflow env passing for changed files ([a8a114c](https://github.com/ai-workflow-space/stock-market-toolkit/commit/a8a114c828a80a8c3623fc82fa402b4510d0cf0f))
* ComparePage UX — Enter adds tickers, (n/5) counter, Add button ([c4ed024](https://github.com/ai-workflow-space/stock-market-toolkit/commit/c4ed0243f36a9bd0762d18c82be2e36a3046e2a1))
* compute MACD and BollingerBands DataFrames directly ([#9](https://github.com/ai-workflow-space/stock-market-toolkit/issues/9)) ([b755724](https://github.com/ai-workflow-space/stock-market-toolkit/commit/b755724fef51533583a5e21d10187cb4a044044d))
* ESLint errors (set-state-in-effect, explicit-any, hook split) + Discord webhook JSON escaping ([fadd0c4](https://github.com/ai-workflow-space/stock-market-toolkit/commit/fadd0c473e0b4557ee83eb56578baf528042abbc))
* handle short-period intraday data gracefully ([95c83f3](https://github.com/ai-workflow-space/stock-market-toolkit/commit/95c83f378657e0897f4a8dfc19f143e40e2e616e))
* only render RSI/MACD chart panes when indicators are active ([6cea117](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6cea11720b9af687073eb8470d967d26ec936381))
* only show chart lines for active indicators, pass active Set to chart components ([9be6a83](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9be6a8356d300b5112179d00c39c886ae10ff42b))
* prevent dropdown flicker with race condition guard ([4c3d736](https://github.com/ai-workflow-space/stock-market-toolkit/commit/4c3d736a45cfc46631973be95252cb89ede6a607))
* push Docker images on PR builds too ([bc5177a](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bc5177adb23e92e47685d483ad3b506e1aa5ba58))
* remove auth from search_symbols in stocks.py - search is public ([5af4280](https://github.com/ai-workflow-space/stock-market-toolkit/commit/5af4280b26fc57ace99142759948da6261f57e50))
* remove auth headers from searchSymbols() - /api/search is public ([8f7b6fd](https://github.com/ai-workflow-space/stock-market-toolkit/commit/8f7b6fd0207befa748b16d982805fd162fdd1861))
* remove branch-name docker tag (feat/ prefix causes invalid tag) ([bec71ca](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bec71ca7de6a72ff0f10e8fb305e07f5a706514b))
* remove duplicate /api prefix location block in nginx.conf ([0b92461](https://github.com/ai-workflow-space/stock-market-toolkit/commit/0b924619d312e329d28d06b218e51ba77f86d448))
* remove emoji from nav/search, add version footer, inject git SHA via Docker build args, remove docker-compose version field ([ee3892d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/ee3892dd140f7b652ce0a7decd568e25d7697d8c))
* remove unused imports from stocks.py (AsyncSession, select, get_db, pandas, time, json) ([36abd5f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/36abd5f8362b5084d722934d5cb33959aaad661a))
* remove unused imports in main.py (pandas, timedelta, Optional) ([6b36662](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6b36662e26d1f826adf6e3ef7754be9122e627de))
* remove unused imports in models.py (Float, Text, relationship) and auth.py (status) ([15acb69](https://github.com/ai-workflow-space/stock-market-toolkit/commit/15acb69e263bcf1e16b8f5982deb255159321685))
* replace asyncpg with aiosqlite for SQLite local dev ([ec15e06](https://github.com/ai-workflow-space/stock-market-toolkit/commit/ec15e06f4c4e8b5c323cbb925c19ee7d4b1112d9))
* replace non-standard cache_control_max_age with standard nginx expires directive ([6f3ac17](https://github.com/ai-workflow-space/stock-market-toolkit/commit/6f3ac17865fc489c08d87a059815532a30af9a6c))
* resolve 9 ESLint errors (set-state-in-effect, no-explicit-any, hook-separation) ([cc1bb0c](https://github.com/ai-workflow-space/stock-market-toolkit/commit/cc1bb0c32a78604b57ae73d68f83a7dc46872822))
* restore docker-publish.yml, comment out broken pytest step, fix code-review opencode install + permissions ([5f26f94](https://github.com/ai-workflow-space/stock-market-toolkit/commit/5f26f94a3ac4c5eddd4e44e6d6c49fa9ab57b8e0))
* restore relationship/Float/Text imports in models.py, fix all 18 ruff/eslint errors from merged PRs ([737d645](https://github.com/ai-workflow-space/stock-market-toolkit/commit/737d6452df9bdb76486026fab7245b327622476b))
* restore yfinance search API (backend + frontend response parsing) ([fee3056](https://github.com/ai-workflow-space/stock-market-toolkit/commit/fee30567036ae06bd2ead2077915c3728bc4dafc))
* set VITE_API_URL= (empty) to prevent double /api prefix in frontend requests ([d24ed04](https://github.com/ai-workflow-space/stock-market-toolkit/commit/d24ed040f291698d188b372ebb3c519232d8253f))
* set VITE_API_URL=/api in Dockerfile, remove stale frontend/.env from Docker build ([361c655](https://github.com/ai-workflow-space/stock-market-toolkit/commit/361c655564b6fa8d2e3a429ef1d79204fdf40ea7))
* simplify Discord webhook payload (use GitHub context vars directly) ([cac9f76](https://github.com/ai-workflow-space/stock-market-toolkit/commit/cac9f76234b38d29364b21468a83e1a77459e8dc))
* unify AlertsPage empty-state button to match header '+ New Alert' button ([f55df69](https://github.com/ai-workflow-space/stock-market-toolkit/commit/f55df690b8ee344f92445df171d0957000159d59))
* use conditional render for indicator lines instead of hide prop ([f95e03d](https://github.com/ai-workflow-space/stock-market-toolkit/commit/f95e03d16592412c2c5efe76938f84de23f49f51))
* use conditional render for indicator lines, fix VITE_API_URL, remove duplicate nginx location block ([164568e](https://github.com/ai-workflow-space/stock-market-toolkit/commit/164568e73f775e790bfced7400df02703c861cb7))
* use official release-please GitHub Action instead of pip install ([586e24f](https://github.com/ai-workflow-space/stock-market-toolkit/commit/586e24ff20e673b940c439e6d9391473cf8fdfeb))
* use relative API URLs to route through nginx proxy instead of localhost:8001 ([9bf8ee7](https://github.com/ai-workflow-space/stock-market-toolkit/commit/9bf8ee7df09dca248e712b15a8aab7f2f9a52397))


### Documentation

* Add comprehensive documentation covering architecture, external services, community tools, setup, and API reference ([bf579fb](https://github.com/ai-workflow-space/stock-market-toolkit/commit/bf579fb8705a9922e831888fdef208b759498c92))
