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
  notes: string;
  isDraft: boolean;
  createdAt: Date;
  receivedAt?: Date;
  submittedAt: Date;
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
  analysisTypeName: string;
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
  analysisTypeIds: number[];
}

export interface SaveResultDto {
  resultId: number;
  measuredValue: number;
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
  phase: string;
  plannedDate: Date;
  actualDate?: Date;
  isOverdue: boolean;
}
