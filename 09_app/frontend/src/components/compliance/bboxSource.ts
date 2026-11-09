// Honest wording for where a finding's highlight box came from (03b_compliance_guardrails, column bbox_source).
export function bboxSourceLabel(source: string | null | undefined): string {
  switch (source) {
    case 'ground_truth':
      return 'Highlight: synthetic ground truth';
    case 'parse_element':
      return 'Highlight: parsed element (approximate)';
    case 'page':
      return 'Highlight: whole page';
    case null:
    case undefined:
    case '':
      return 'No highlight location for this finding';
    default:
      return `Highlight: ${source} (approximate)`;
  }
}
