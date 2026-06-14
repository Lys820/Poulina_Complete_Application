export interface Laboratory {
  id: number;
  name: string;
  description: string;
  address: string;
}

export interface AnalysisType {
  id: number;
  name: string;
  description: string;
  referenceMin: number;
  referenceMax: number;
  unit: string;
}
