import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Laboratory, AnalysisType } from '../models/laboratory.model';

@Injectable({ providedIn: 'root' })
export class LaboratoryService {
  constructor(private http: HttpClient) {}

  getLaboratories(): Observable<Laboratory[]> {
    return this.http.get<Laboratory[]>(`${environment.apiUrl}/laboratories`);
  }

  getAnalysisTypes(): Observable<AnalysisType[]> {
    return this.http.get<AnalysisType[]>(`${environment.apiUrl}/analysistypes`);
  }
}
