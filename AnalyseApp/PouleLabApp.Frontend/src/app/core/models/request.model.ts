export interface RequestListDto {
  id: number;
  status: string;
  laboratoryName: string;
  clientName: string;
  createdAt: Date;
  receivedAt?: Date;
  isDraft: boolean;
  samplesCount: number;
}

export interface RequestDetailDto {
  id: number;
  status: string;
  brand: string;
  notes: string;
  isDraft: boolean;
  createdAt: Date;
  receivedAt?: Date;
  submittedAt: Date;
  laboratoryId: number;
  laboratoryName: string;
  clientId: string;
  clientName: string;
  clientEmail: string;
  assignedToId?: string;
  assignedToName?: string;
  samples: SampleDetailDto[];
}

export interface SampleDetailDto {
  id: number;
  type: string;
  characteristics: string;
  quantity: number;
  unit: string;
  results: AnalysisResultDetailDto[];
}

export interface AnalysisResultDetailDto {
  id: number;
  analysisName: string;
  measuredValue: number;
  lowerBound: number;
  upperBound: number;
  unit: string;
  isAnomaly: boolean;
  recordedAt: Date;
}

export interface CreateRequestDto {
  laboratoryId: number;
  notes: string;
  isDraft: boolean;
  samples: CreateSampleDto[];
}

export interface CreateSampleDto {
  type: string;
  characteristics: string;
  quantity: number;
  unit: string;
  analysisNames: string[];
}

export interface SaveResultDto {
  resultId: number;
  measuredValue: number;
  lowerBound: number;
  upperBound: number;
  unit: string;
}

export interface AuditLogDto {
  id: number;
  action: string;
  performedBy: string;
  oldValue?: string;
  newValue?: string;
  performedAt: Date;
}

export interface DeadlineDto {
  id: number;
  sampleId: number;
  sampleType: string;
  isPerishable: boolean;
  expiryDate?: Date;
  urgencyLevel: string;
  urgencyDescription: string;
}

export interface SetDeadlineDto {
  sampleId: number;
  isPerishable: boolean;
  expiryDate?: string;
  urgencyLevel: string;
  urgencyDescription: string;
}
