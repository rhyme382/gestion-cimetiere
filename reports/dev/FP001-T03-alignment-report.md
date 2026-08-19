# FP001-T03 — TypeScript Contracts Alignment Report

## Summary

Successfully aligned TypeScript bindings, Tauri command client, and React hooks with the new Rust DTO contracts introduced in FP001-T02. The task ensures frontend type safety and contract consistency across municipality and cemetery operations.

## Changes Made

### 1. TypeScript Bindings Update (`src/types/bindings.ts`)

#### Added Municipality Types
- `MunicipalityDTO` — Complete municipality data structure with:
  - Core fields: id, name, insee_code
  - Optional fields: postal_code, email, department, region, notes
  - Timestamps: created_at, updated_at
- `CreateMunicipalityRequest` — Request structure for creating municipalities
- `UpdateMunicipalityRequest` — Partial request structure for updating municipalities

#### Extended Cemetery Types
- `CemeteryDTO` — Added new fields aligned with Rust backend:
  - `municipality_id` (number | null) — Link to associated municipality
  - `address` (string | null) — Cemetery address
  - `is_active` (number) — Active status flag
- Updated `CreateCemeteryRequest` to include optional `municipality_id` and `address`
- Updated `UpdateCemeteryRequest` to support optional `municipality_id`, `address`, and `is_active`

### 2. Tauri Command Client Update (`src/lib/tauri.ts`)

#### Added Municipality Commands
- `listMunicipalities()` — Fetch all municipalities
- `getMunicipality(id: number)` — Fetch single municipality
- `createMunicipality(req: CreateMunicipalityRequest)` — Create new municipality
- `updateMunicipality(id: number, req: UpdateMunicipalityRequest)` — Update existing municipality
- `deleteMunicipality(id: number)` — Delete municipality

All commands properly typed and invoke correct Rust command names with matching parameter structures.

### 3. React Hooks Implementation

#### New File: `src/hooks/useMunicipalities.ts`
Created consistent hook module following existing patterns:
- `useMunicipalities(options?)` — Query hook for listing municipalities
- `useMunicipality(id, options?)` — Query hook for fetching single municipality
- `createMunicipalityAsync(request)` — Async function for creation
- `updateMunicipalityAsync(id, request)` — Async function for updates
- `deleteMunicipalityAsync(id)` — Async function for deletion

#### Updated: `src/hooks/index.ts`
- Exported all municipality hooks
- Added municipality types to type exports

### 4. Test Coverage (`src/__tests__/`)

#### Bindings Tests (`bindings.test.ts`)
Added 4 new test cases:
- MunicipalityDTO structure validation
- MunicipalityDTO nullable fields handling
- CreateMunicipalityRequest contract validation
- UpdateMunicipalityRequest partial update contract

Enhanced Cemetery Tests:
- Updated CemeteryDTO to verify new fields (municipality_id, address, is_active)
- Added test for inactive cemetery status

#### Tauri Client Tests (`tauri.test.ts`)
Added comprehensive municipality command tests:
- `listMunicipalities()` invocation and empty list handling
- `getMunicipality(id)` with proper parameter passing
- `createMunicipality(req)` with full request structure
- `updateMunicipality(id, req)` with partial updates
- `deleteMunicipality(id)` void return type

Enhanced Cemetery Tests:
- Updated create/update cemetery tests to include new fields
- Verified new fields are properly serialized/deserialized

## Contract Stability Verification

### Rust ↔ TypeScript Synchronization

| Entity | Rust DTO | TypeScript DTO | Status |
|--------|----------|----------------|--------|
| MunicipalityDTO | ✓ | ✓ | Aligned |
| CreateMunicipalityRequest | ✓ | ✓ | Aligned |
| UpdateMunicipalityRequest | ✓ | ✓ | Aligned |
| CemeteryDTO + municipality_id | ✓ | ✓ | Aligned |
| CemeteryDTO + address | ✓ | ✓ | Aligned |
| CemeteryDTO + is_active | ✓ | ✓ | Aligned |

### Tauri Command Contracts

| Command | Backend | Client | Status |
|---------|---------|--------|--------|
| list_municipalities | #[tauri::command] | invoke() | ✓ |
| get_municipality | #[tauri::command] | invoke(id) | ✓ |
| create_municipality | #[tauri::command] | invoke(req) | ✓ |
| update_municipality | #[tauri::command] | invoke(id, req) | ✓ |
| delete_municipality | #[tauri::command] | invoke(id) | ✓ |
| list_cemeteries | #[tauri::command] | invoke() | ✓ |
| get_cemetery | #[tauri::command] | invoke(id) | ✓ |
| create_cemetery | #[tauri::command] | invoke(req) | ✓ |
| update_cemetery | #[tauri::command] | invoke(id, req) | ✓ |

## Test Results

```
✓ Test Files  2 passed (2)
✓ Tests  50 passed (50)
  Duration: 705ms
```

### Test Breakdown
- **bindings.test.ts**: 30 tests covering all DTO shapes
- **tauri.test.ts**: 20 tests covering command invocations

## Files Modified

### Modified Files
- `src/types/bindings.ts` — Added Municipality types, extended Cemetery types
- `src/lib/tauri.ts` — Added municipality commands
- `src/hooks/index.ts` — Exported municipality hooks and types
- `src/__tests__/bindings.test.ts` — Added municipality and extended cemetery tests
- `src/__tests__/tauri.test.ts` — Added municipality command tests

### New Files
- `src/hooks/useMunicipalities.ts` — Municipality React hooks

## Error Handling

All command functions properly handle and propagate errors:
- Rust `AppError` mapped to `ApiErrorResponse` with typed error codes
- Supported error types: NOT_FOUND, INVALID_INPUT, DATABASE_ERROR, INTERNAL_ERROR, DUPLICATE
- TypeScript client and hooks preserve error details for UI error handling

## Next Steps

1. **UI Implementation**: Use new municipality and cemetery hooks in React components
2. **Form Integration**: Implement forms for creating/updating municipalities
3. **Data Validation**: Add client-side validation for municipality data
4. **Municipality List View**: Build UI component for browsing municipalities
5. **Cemetery-Municipality Linking**: Implement UI for associating cemeteries with municipalities

## Acceptance Criteria Status

✅ TypeScript bindings reflect Rust DTOs for municipality and cemetery  
✅ `src/lib/tauri.ts` invokes commands with correct parameter names  
✅ Tests lock down contract stability  
✅ No breaking changes to existing commands  
✅ Hooks follow existing React patterns  
✅ All tests pass (50/50)  

## Notes

- The municipality reference is optional on cemeteries (nullable foreign key)
- Cemetery addresses are optional, allowing legacy data without addresses
- The `is_active` field enables soft-deletes for cemetery records
- All commands use proper error mapping for user-friendly error messages
