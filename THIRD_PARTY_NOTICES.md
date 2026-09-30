# Third-party software

The MIT license in this repository covers the application's own source. Dependencies and
container components retain their own licenses, notices, and distribution obligations.

| Component  | Upstream / license information                                                        |
| ---------- | ------------------------------------------------------------------------------------- |
| yt-dlp     | https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE and its THIRD_PARTY_LICENSES.txt |
| yt-dlp-ejs | https://github.com/yt-dlp/ejs                                                         |
| curl-cffi  | https://github.com/lexiforest/curl_cffi/blob/main/LICENSE ; bundled curl notices apply |
| FFmpeg     | https://ffmpeg.org/legal.html ; Debian package license/build configuration applies    |
| FastAPI    | https://github.com/fastapi/fastapi/blob/master/LICENSE                                |
| Starlette  | https://github.com/Kludex/starlette/blob/main/LICENSE.md                              |
| Uvicorn    | https://github.com/Kludex/uvicorn/blob/main/LICENSE.md                                |
| Authlib | https://github.com/authlib/authlib/blob/main/LICENSE ; BSD 3-Clause |
| joserfc | https://github.com/authlib/joserfc ; bundled license applies |
| cryptography | https://github.com/pyca/cryptography ; bundled Apache/BSD notices apply |
| httpx2 | https://github.com/pydantic/httpx2 ; bundled license applies |
| Python     | https://docs.python.org/3/license.html                                                |
| Node.js    | https://github.com/nodejs/node/blob/main/LICENSE                                      |
| uv         | https://github.com/astral-sh/uv                                                       |

The container installs Debian's FFmpeg packages without copying or relicensing their source.
Package copyright notices remain under `/usr/share/doc`. Review the actual build and source
availability when redistributing an image. Exact Python and development npm dependency versions
are recorded in `uv.lock` and `package-lock.json`. No upstream source code, third-party branding,
downloaded videos, or user data is vendored into this repository.
