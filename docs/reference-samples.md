# Reference Samples (Ground Truth / Golden Dataset)

This directory contains human-curated "before-and-after" benchmark pairs:
* **Input**: The original employee resume (PDF) with its unstructured/creative layout.
* **Curated Output**: The approved, human-standardized Word document (`.docx`) following the official Coforge corporate template.

These pairs serve as the baseline ground truth for:
1. Validating extraction fidelity against manual recruiter output.
2. Checking table structures, bullet indentations, and skill category bolding.
3. Regression testing future prompt and schema iterations.

### Datasets:
- **`pavan_p/`**: Salesforce Data Cloud & Analytics Consultant profile (multi-project structure, categorized skills).
- **`sreenivasa_g/`**: Salesforce Analytics Consultant profile (demonstrates handling of unstated project durations).
