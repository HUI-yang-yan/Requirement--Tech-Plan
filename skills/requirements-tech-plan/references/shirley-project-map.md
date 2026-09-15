# Shirley Project Map

Use this when locating implementation points in the Shirley CRM repository.

## Roots

- `shirley-admin`: CRM frontend.
- `shirley-web`: Java backend.
- `docs`: technical方案 output directory.

## Backend Layout

- `shirley-web/web/src/main/java`: Controller layer.
- `shirley-web/biz/src/main/java`: Biz orchestration layer.
- `shirley-web/service/src/main/java`: Service layer.
- `shirley-web/domain/src/main/java`: PO/database entity layer.
- `shirley-web/api/src/main/java`: Req/Resp/VO/DTO layer.
- `shirley-web/dao` or mapper packages: Mapper/DAO layer when present.

## Frontend Layout

- `shirley-admin/src/views`: pages and business components.
- `shirley-admin/src/api`: API clients.
- `shirley-admin/src/router` or route modules: route entry points when present.

## Search Strategy

Start with `scripts/collect_evidence.py` to obtain cross-layer candidates in one call. Its cache is valid only while the repository fingerprint is unchanged. The result is a recall aid, never the final source of truth.

Then open the current source around candidate locations. Use `rg -n` to extend or repair the call chain. Avoid loading large Biz/Service files in full when a narrow line range is sufficient.

Fall back to a broader repository search when any of these is true:

- `requires_deep_search` is `true`.
- The expected Controller, Biz, Service, Mapper/domain, frontend, or test connection is missing.
- A frontend request cannot be matched to a backend route.
- A status or field source remains unclear.
- A candidate path, hash, method, or line no longer matches the current file.

Combine Chinese terms with English/domain aliases during fallback searches:

- 退费: `refund`, `Refund`, `退费`, `refundRec`, `refund_rec`
- 申诉: `appeal`, `Appeal`, `申诉`, `refundAppeal`
- 审批: `approval`, `Approval`, `审批`, `approve`, `reqContent`, `reqMap`
- 学员: `student`, `Student`, `学员`, `studentId`
- 班级: `class`, `Class`, `班级`, `classId`
- 赠品: `gift`, `Gift`, `赠品`
- 库存: `stock`, `Stock`, `库存`, `remain`
- 删除: `delete`, `del`, `remove`, `删除`
- 状态: `status`, `Status`, `状态`, `pen`, `proc`, `apr`, `rej`, `cancel`

## Line Number Capture

Use commands that preserve line numbers, such as:

```powershell
rg -n "keyword|methodName" D:\project\shirley-web -S
```

For a planned modification, locate the nearest exact insertion point with `path:line`. If a helper method will be added, identify the surrounding method or class closing area by line number.

Never copy a line number from cached evidence directly into the technical方案. Re-open the current file and verify the method, surrounding code, and line number first.

## Minimum-Change Bias

- Backend is the final authority for destructive or permission-sensitive behavior.
- Frontend changes are for visibility and operator ergonomics, not security.
- Prefer existing status values and existing request/response fields.
- Prefer current service/biz patterns over new abstractions.
- Add small helper methods for repeated conditions or readable chain operations.
