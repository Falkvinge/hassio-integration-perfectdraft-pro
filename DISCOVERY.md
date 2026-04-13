# PerfectDraft Pro API Discovery

## TL;DR — What Actually Works

**Authentication:**
1. Load `https://www.perfectdraft.com/en-gb/customer/account/login` in a real browser
2. Execute `grecaptcha.enterprise.execute('6LcZQiUoAAAAAAO3JUjLiT470c-pNXbWyepuvMtV', {action: 'Magento/login'})` to get a reCAPTCHA token
3. POST to `https://api.perfectdraft.com/authentication/sign-in` with `{email, password, recaptchaToken, recaptchaAction: "Magento/login"}` and header `x-api-key: cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10`
4. Returns `{AccessToken, IdToken, RefreshToken}`

**Token refresh (no reCAPTCHA needed, ever again):**
- POST directly to AWS Cognito: `https://cognito-idp.eu-west-1.amazonaws.com/`
- Header: `X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth`
- Body: `{AuthFlow: "REFRESH_TOKEN_AUTH", ClientId: "57ddq2ppqg2jcpup06r2g1deur", AuthParameters: {REFRESH_TOKEN: "..."}}`
- Returns fresh `AccessToken` and `IdToken` (1 hour TTL). The original `RefreshToken` stays valid.

**Data endpoints:**
- `GET /api/me` → user profile with `perfectdraftMachines[].id`
- `GET /api/perfectdraft_machines/{id}` → full machine telemetry in `details` object

**Key constants:**
- API base: `https://api.perfectdraft.com`
- x-api-key: `cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10`
- reCAPTCHA web key: `6LcZQiUoAAAAAAO3JUjLiT470c-pNXbWyepuvMtV` (from perfectdraft.com login page)
- reCAPTCHA action: `Magento/login`
- Cognito region: `eu-west-1`
- Cognito User Pool: `eu-west-1_UXWVyvlHR`
- Cognito Client ID: `57ddq2ppqg2jcpup06r2g1deur`

---

## The Journey

### 1. Starting from community attempts

The only existing integration attempt was [matthewcky2k/homeassistant-perfectdraft](https://github.com/matthewcky2k/homeassistant-perfectdraft), discussed in a [Home Assistant forum thread](https://community.home-assistant.io/t/perfect-draft-integration/505209). It provided the initial clues:

- **API base URL**: `https://api.perfectdraft.com`
- **Sign-in endpoint**: `POST /authentication/sign-in`
- **x-api-key**: `cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10`
- **reCAPTCHA site key**: `6LdrqmApAAAAAB_kTEHVnx9pua3TMurf4i75a-aQ`
- **Request body**: `{email, password, recaptchaToken, recaptchaAction: "Android_recaptchaThatWorks/login"}`
- **Response**: `{AccessToken, IdToken, RefreshToken}`
- **Data endpoints**: `GET /api/me`, `GET /api/perfectdraft_machines/{id}`

The existing integration didn't work because:
- It asked users to manually paste a reCAPTCHA token (tokens expire in ~2 minutes)
- It used synchronous `requests` instead of async `aiohttp`
- No `DataUpdateCoordinator` (each sensor polled independently → IP bans)
- Broken HACS packaging (files didn't download properly)
- No token refresh logic

A forum user had sniffed the app traffic and confirmed: *"It's only used at the point of initial sign-in to the API, once you are authenticated you have a token to use."* This was the key insight that refresh tokens existed.

### 2. Server-side reCAPTCHA token generation (FAILED)

**Approach**: Use the reCAPTCHA anchor/reload HTTP endpoints to generate tokens without a browser.

**What happened**: The anchor endpoint (`/recaptcha/api2/anchor` and `/recaptcha/enterprise/anchor`) returned tokens, but the reload endpoint generated tokens without the correct `action` binding. The API validated that the action embedded in the token matched `"Android_recaptchaThatWorks/login"`.

**Error**: `"The reCAPTCHA action does not match the expected action."`

**Why it failed**: reCAPTCHA v3/Enterprise embeds the action string cryptographically in the token during `grecaptcha.execute()`. The anchor/reload HTTP flow doesn't support specifying a custom action — that's a client-side-only feature.

### 3. Browser-based reCAPTCHA on HA external step (FAILED)

**Approach**: Serve a small HTML page from Home Assistant during the config flow that loads the reCAPTCHA JS and generates a token invisibly.

**What happened**: The reCAPTCHA widget displayed "ERROR for site owner: Invalid domain" in the corner. The `execute()` call either failed silently or returned a garbage token.

**Why it failed**: The reCAPTCHA site key `6LdrqmAp...` was registered as an **Android-only** key in Google's reCAPTCHA Enterprise console. It was never meant to work in a web browser. The web `api.js` rejected it because the domain (`yellow:8123`) wasn't in the allowed list — and no web domain would be, because it's not a web key.

### 4. Playwright headless browser with correct action (FAILED)

**Approach**: Use Playwright to load a page on `perfectdraft.com` (via route interception), execute reCAPTCHA with the correct action string, and use the resulting token.

**What happened**: Tokens were generated with the correct action. The API accepted the action but rejected the score.

**Error**: `"The reCAPTCHA score is below the set threshold."`

**Why it failed**: reCAPTCHA Enterprise assigns a trust score based on browser behavior, device fingerprinting, and interaction patterns. Headless browsers (even with stealth patches, mobile user agents, and anti-detection measures) consistently received low scores. Tried:
- Headless Chromium
- Headed Chromium
- Mobile user agent (Pixel 8)
- `playwright-stealth` library
- `--disable-blink-features=AutomationControlled`
- Removing `navigator.webdriver`

All received scores below PerfectDraft's threshold. reCAPTCHA Enterprise is specifically designed to detect automated browsers.

### 5. Discovering the web reCAPTCHA key (FAILED initially, SUCCEEDED later)

**Approach**: Check if `perfectdraft.com` uses a different reCAPTCHA key for their web login.

**Discovery**: The web login page at `perfectdraft.com/en-gb/customer/account/login` loads reCAPTCHA Enterprise with a **different** key: `6LcZQiUoAAAAAAO3JUjLiT470c-pNXbWyepuvMtV`, using action `Magento/login`.

**First test**: Generated a token with Playwright using this web key and `Magento/login` action, sent it to `/authentication/sign-in`.

**Result**: `"The reCAPTCHA score is below the set threshold."` — same score problem from headless browser.

**Key insight**: The API **did accept** the web key with `Magento/login` action. The only issue was the automated browser's low score. A real human browser would get a high enough score. This insight was filed away and became the breakthrough later.

### 6. PCAPdroid network capture (FAILED)

**Approach**: Capture the PerfectDraft app's network traffic on a real phone using PCAPdroid with TLS decryption.

**What happened**: First capture (without TLS decryption) showed only encrypted traffic. Second capture (with TLS decryption enabled) also showed only encrypted traffic.

**Why it failed**: The PerfectDraft app uses **certificate pinning**. When PCAPdroid's MITM CA certificate was active, the app's OkHttp client rejected the connection. The app refused to log in entirely when MITM was detected.

### 7. ADB token extraction (NOT ATTEMPTED)

**Approach**: Connect the phone via USB debugging and extract tokens from the app's storage.

**Why not attempted**: The user (rightfully) refused to enable USB debugging on a phone with banking certificates, citing the risk of WiFi debugging being enabled by default on some Android devices.

### 8. APK decompilation and analysis

**Approach**: Download and decompile the PerfectDraft APK to understand the auth flow.

**Source**: Downloaded PerfectDraft v3.5.5 from apk.cafe (split APK bundle: base + arm64 + en + xxhdpi).

**Tools**: `apktool` for smali decompilation, `strings` for Hermes bytecode analysis.

**Key discoveries from the APK**:

The app is built with **Expo/React Native** with **Hermes** bytecode. The JS bundle is compiled to Hermes binary format, making it harder to read than plain JS.

**BuildConfig.smali** revealed all configuration constants:
```
API_KEY = cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10
BASE_URL = https://api.perfectdraft.com
CAPTCHA_KEY = 6LdXriEoAAAAAJbpl0ApCsOpaRjLfKfKpxn07Hv4  (third key!)
CAPTCHA_SITE_KEY = https://www.perfectdraft.com
PERFECTSERVE_API_KEY = 540297f2-b287-4adb-afc1-cb2166cfcb14
NUCLEUS_URL = https://api.perfectdraft.com
ONBASS_URL = https://eur-04530-pdiot-onbass-uks-prod-fnapp.azurewebsites.net/api
KEG_RETURN_API = https://keg-return-service.api.perfectdraft.tech
```

**Hermes bundle string extraction** revealed a second auth system:
- `/auth/signin` — a .NET backend (separate from the Cognito `/authentication/sign-in`)
- `/auth/renewaccesstokens` — **token refresh without reCAPTCHA!**
- `/auth/signout`, `/auth/changepassword`, `/auth/confirmsignup`
- `/api/perfectdraft_machines/`, `/api/perfectdraft_machine_kegs`
- `@google-cloud/recaptcha-enterprise-react-native` — confirms Enterprise reCAPTCHA via native Android SDK

**The refresh endpoint discovery**: Probing `/auth/renewaccesstokens` with an empty body returned `{"UserId":["The UserId field is required."],"RefreshToken":["The RefreshToken field is required."]}` — confirming it exists and telling us the exact field names. This endpoint does NOT require reCAPTCHA.

### 9. The third reCAPTCHA key (FAILED)

**Approach**: The APK's `CAPTCHA_KEY` (`6LdXriEoAAAAAJbpl0ApCsOpaRjLfKfKpxn07Hv4`) was different from both the Android key and the web key. Tested it via anchor/reload and Playwright.

**What happened**: Google's reCAPTCHA JS returned 400 Bad Request when loaded with this key. The anchor endpoint returned pages without tokens.

**Why it failed**: This is also an **Android-only** key. The `CAPTCHA_SITE_KEY = https://www.perfectdraft.com` in the config is misleading — it's used as a parameter in the Android reCAPTCHA Enterprise SDK call, not as a web origin. All three keys are Android-only:
- `6LdrqmAp...` — from community research
- `6LdXriEo...` — from APK BuildConfig
- `6LcZQiUo...` — from perfectdraft.com web page (this one IS a web key)

### 10. Android emulator approach (FAILED)

**Approach**: Run the PerfectDraft app in an Android emulator on the battlestation, with mitmproxy intercepting traffic.

**What happened**: Installed Android SDK, created an x86_64 AVD with Google APIs image, installed the APK.

**Failure 1**: The APK required split APKs (`INSTALL_FAILED_MISSING_SPLIT`). Installed with all splits.

**Failure 2**: The app crashed with `SoLoaderDSONotFoundError: couldn't find DSO to load: libreactnative.so`. The arm64 native libraries couldn't run on the x86_64 emulator despite ARM translation support — React Native's native bridge was too complex for the translation layer.

**Failure 3**: ARM64 system images exist but the Android emulator binary doesn't support ARM64 on x86_64 hosts (`FATAL: Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host`).

### 11. K8s ARM64 pod approach (FAILED)

**Approach**: Use a Raspberry Pi 4B node in the Kubernetes cluster to run an ARM64 Android emulator natively.

**What happened**: Created a pod on an ARM64 node, installed Java and Android SDK. The `emulator` package doesn't exist for ARM64 Linux — Google only distributes it for x86_64.

**Why it failed**: No ARM64 Android emulator binary exists. Would need QEMU to boot an Android image, which would be extremely slow on a Pi 4B inside a K8s pod without KVM.

### 12. APK patching — removing cert pinning (FAILED, multiple attempts)

**Approach**: Modify the PerfectDraft APK to disable certificate pinning, install on the user's real phone, capture traffic with PCAPdroid.

**Discovery**: Analysis of the smali code revealed that OkHttp's `CertificatePinner.Builder.add()` is **never called** — there are no hardcoded certificate pins. The app relies solely on Android's default trust store behavior (which doesn't trust user-installed CAs on Android 7+).

**Attempt 1 — Full apktool decompile/rebuild**: Decompiled with `apktool d`, added `network_security_config.xml` trusting user CAs, patched manifest, no-oped `CertificatePinner.check()` in smali, rebuilt with `apktool b`. App crashed immediately on launch. Apktool corrupted the Hermes bytecode or resource references during the decompile/recompile cycle.

**Attempt 2 — apktool with `-s` (skip DEX)**: Decompiled resources only, kept DEX files intact, added network security config, rebuilt. App still crashed — the manifest and `resources.arsc` were subtly corrupted by apktool's resource recompilation.

**Attempt 3 — Binary manifest patching**: Extracted the apktool-rebuilt manifest and `resources.arsc`, injected them into the original APK via zip commands, keeping all DEX files original. App crashed — the `resources.arsc` from apktool didn't match the original resource IDs (app icon was missing, replaced with generic Android icon).

**Attempt 4 — DEX-only patching**: Created a `TrustAllCerts` class in smali, patched `OkHttpClientProvider.createClientBuilder()` to inject a trust-all `SSLSocketFactory`. Rebuilt only `classes3.dex` via apktool, injected it into the original APK keeping everything else byte-for-byte identical. Manifest and resources verified identical via md5sum. App reported "not compatible with your phone" — the original manifest's `requiredSplitTypes` attribute demanded the architecture split APK.

**Attempt 5 — Binary manifest + DEX patch**: Patched the `requiredSplitTypes` string in the binary manifest by finding the UTF-16LE encoded string and replacing it with spaces (same byte length). Combined with the DEX patch. This was never tested on the phone because the user was (understandably) fatigued by the cycle.

### 13. The breakthrough — real browser on perfectdraft.com

**Approach**: Revisiting discovery #5 — the web reCAPTCHA key works, it just needs a real browser with a high trust score.

**The test**: User opened `https://www.perfectdraft.com/en-gb/customer/account/login` in Chrome, opened the dev console, and ran:

```javascript
grecaptcha.enterprise.execute('6LcZQiUoAAAAAAO3JUjLiT470c-pNXbWyepuvMtV', {action: 'Magento/login'}).then(t => console.log(t))
```

This generated a valid token from a real browser on the real domain — high reCAPTCHA score.

**The auth call**:
```
POST https://api.perfectdraft.com/authentication/sign-in
x-api-key: cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10
{email, password, recaptchaToken: <token>, recaptchaAction: "Magento/login"}
```

**Result**: `200 OK` with `{AccessToken, IdToken, RefreshToken}`.

**Why it worked**: The API's Cognito Lambda trigger validates the reCAPTCHA token against Google's assessment API. It checks:
1. The action matches a configured action (both `Android_recaptchaThatWorks/login` and `Magento/login` are configured)
2. The score is above a threshold
3. The token is valid for one of the registered site keys

The web key (`6LcZQiUo...`) is registered for `perfectdraft.com`. A real browser on that domain gets a high score. The API accepts tokens from this key with the `Magento/login` action.

### 14. Cognito direct refresh

**Discovery**: Decoding the JWT `AccessToken` revealed:
- `iss`: `https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_UXWVyvlHR`
- `client_id`: `57ddq2ppqg2jcpup06r2g1deur`
- `sub`: the user's UUID

**The refresh call**:
```
POST https://cognito-idp.eu-west-1.amazonaws.com/
Content-Type: application/x-amz-json-1.1
X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth
{AuthFlow: "REFRESH_TOKEN_AUTH", ClientId: "57ddq2ppqg2jcpup06r2g1deur", AuthParameters: {REFRESH_TOKEN: "..."}}
```

**Result**: `200 OK` with fresh `AccessToken` and `IdToken` (1 hour TTL).

This bypasses the API gateway entirely — no reCAPTCHA, no x-api-key, no rate limiting. The refresh token appears to be long-lived (standard Cognito default is 30 days).

### 15. Full API mapping

With valid tokens, the complete API surface was mapped:

**`GET /api/me`** — User profile:
```json
{
  "id": 2556952,
  "cognitoId": "8a1289be-...",
  "email": "...",
  "perfectdraftMachines": [{"id": 401294, "deviceId": "...", "type": "pd_pro"}],
  "country": {"countryCode": "DE"}
}
```

**`GET /api/perfectdraft_machines/{id}`** — Machine telemetry:
```json
{
  "id": 401294,
  "type": "pd_pro",
  "setting": {
    "temperature": 3,
    "temperatureMin": 3,
    "temperatureMax": 7,
    "temperatureUnit": "C",
    "mode": "standard",
    "boost": false
  },
  "details": {
    "serialNumber": "111EU2516001686",
    "firmwareVersion": "v3.16.0-5",
    "temperature": 3,
    "displayedBeerTemperatureInCelsius": 3,
    "displayedBeerTemperatureInFahrenheit": 37,
    "kegVolume": 5.13,
    "kegPressure": 114.33,
    "doorClosed": true,
    "connectedState": true,
    "numberOfPoursSinceStartup": 30,
    "volumeOfLastPour": 0.289,
    "durationOfLastPour": 3701,
    "kegType": "PD",
    "errorCodes": 0
  }
}
```

**`GET /api/perfectdraft_machine_kegs`** — Keg history (global, not per-machine filterable without the machine's own keg endpoint).

**`GET /api/products/{id}`** — Minimal product data (just `{id}`), no keg name or image available from this API.

### Summary of reCAPTCHA keys

| Key | Source | Type | Works from browser? |
|-----|--------|------|-------------------|
| `6LdrqmAp...` | Community research / forum | Android Enterprise | No |
| `6LdXriEo...` | APK BuildConfig | Android Enterprise | No |
| `6LcZQiUo...` | perfectdraft.com login page | **Web Enterprise** | **Yes** |

### Summary of auth endpoints

| Endpoint | reCAPTCHA required? | Notes |
|----------|-------------------|-------|
| `POST /authentication/sign-in` | Yes (Cognito + Lambda trigger) | Accepts web key with `Magento/login` |
| `POST /auth/signin` | Yes (.NET backend) | Always returns "Captcha Failure" without valid token |
| `POST /auth/renewaccesstokens` | No | Needs `{UserId, RefreshToken}`, returned 409 Conflict in testing |
| Cognito `InitiateAuth` | **No** | Direct Cognito call, works perfectly for refresh |

---

## Why This Succeeded Where Others Failed

Every previous attempt to build a PerfectDraft Home Assistant integration hit the reCAPTCHA wall and stopped. The forum thread has been open since December 2022. People got IP-banned, gave up on token generation, built broken integrations that asked users to paste ephemeral hex codes. The integration was widely considered impossible without PerfectDraft's cooperation.

The breakthrough came from connecting three observations that nobody had put together before:

1. **PerfectDraft's web store uses a different reCAPTCHA key than the mobile app** — and the API accepts tokens from both. Everyone focused on the Android key from the app traffic (`6LdrqmAp...`), which is an Android-only Enterprise key that cannot generate valid tokens from any browser. But the Magento web store at `perfectdraft.com` loads a *web* Enterprise key (`6LcZQiUo...`) that works from any browser on that domain. The API's Cognito Lambda trigger is configured to accept tokens from either key.

2. **The Cognito User Pool can be called directly for token refresh, bypassing the API gateway entirely.** The reCAPTCHA check lives in a Lambda trigger on the API gateway's `/authentication/sign-in` endpoint. But the underlying Cognito User Pool (`eu-west-1_UXWVyvlHR`) accepts standard `REFRESH_TOKEN_AUTH` calls with no reCAPTCHA, no API key, no rate limiting. The pool ID and client ID were extracted from the JWT claims in the access token. This means reCAPTCHA is only needed once — at initial sign-in — and never again.

3. **A real human browser on `perfectdraft.com` gets a high enough reCAPTCHA score.** Automated browsers (Playwright, headless Chrome, even headed Chrome with stealth patches) consistently received scores below PerfectDraft's threshold. But the reCAPTCHA check is score-based, not binary — a real user's browser session on the legitimate domain passes easily. The one-time setup cost of running a console command on `perfectdraft.com` is an acceptable UX trade-off for an integration that then runs autonomously forever.

Each of these observations was individually discoverable. The first required checking the web store's login page source. The second required decoding a JWT. The third required testing the web key against the API and understanding why the score mattered. But nobody had connected all three into a working auth flow — until now.
