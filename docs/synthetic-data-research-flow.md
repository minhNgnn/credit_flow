> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# Synthetic data research flow (English)

A single flowchart (below, with Vietnamese labels) of how the synthetic dataset is produced:

1. Read PRD 1.1 — Table 9, split it into 11 datasets and their mandatory fields.
2. Build the dependency graph and shared keys.
3. Research official sources, then classify each source:
   - **Official aggregate/taxonomy** → whitelist crawl and freeze a snapshot.
   - **Product/policy reference** → curate manually, with version + citation.
   - **PII/customer/private data** → never crawl; generate synthetic data.
4. By data type: numbers, IDs, dates, policies, labels → **deterministic generator**; non-decisive narrative → Data Designer / OpenAI spike.
5. Validate with schema + invariants + cross-dataset checks → freeze clean master datasets → apply mutation overlays → **Case Assembler** (final step).

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

```mermaid
flowchart TD
    A["Đọc PRD 1.1 — Bảng 9"] --> B["Tách 11 datasets và trường bắt buộc"]
    B --> C["Lập dependency graph và shared keys"]
    C --> D["Research nguồn chính thức"]
    D --> E{"Loại nguồn"}
    E -->|"Official aggregate/taxonomy"| F["Whitelist crawl và freeze snapshot"]
    E -->|"Product/policy reference"| G["Curate thủ công + version + citation"]
    E -->|"PII/customer/private data"| H["Không crawl — sinh synthetic"]
    F --> I{"Loại dữ liệu"}
    G --> I
    H --> I
    I -->|"Số, ID, ngày, policy, label"| J["Deterministic generator"]
    I -->|"Narrative không quyết định"| K["Data Designer/OpenAI spike"]
    J --> L["Schema + invariants + cross-dataset checks"]
    K --> L
    L --> M["Freeze clean master datasets"]
    M --> N["Mutation overlays"]
    N --> O["Case Assembler — bước cuối"]
```
