import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  RequestListDto,
  RequestDetailDto,
  CreateRequestDto,
  SaveResultDto,
  AuditLogDto,
  DeadlineDto,
} from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class RequestService {
  private url = `${environment.apiUrl}/requests`;

  constructor(private http: HttpClient) {}

  getAll(status?: string): Observable<RequestListDto[]> {
    const params = status ? new HttpParams().set('status', status) : undefined;
    return this.http.get<RequestListDto[]>(this.url, { params });
  }

  getById(id: number): Observable<RequestDetailDto> {
    return this.http.get<RequestDetailDto>(`${this.url}/${id}`);
  }

  create(dto: CreateRequestDto): Observable<RequestDetailDto> {
    return this.http.post<RequestDetailDto>(this.url, dto);
  }

  submit(id: number): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/submit`, {});
  }

  receive(id: number): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/receive`, {});
  }

  assign(id: number, analystId: string): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/assign`, JSON.stringify(analystId), {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  analystAccept(id: number): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/analyst-accept`, {});
  }

  analystReject(id: number, reason: string): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(
      `${this.url}/${id}/analyst-reject`,
      JSON.stringify(reason),
      { headers: { 'Content-Type': 'application/json' } },
    );
  }

  saveResults(id: number, results: SaveResultDto[]): Observable<RequestDetailDto> {
    return this.http.post<RequestDetailDto>(`${this.url}/${id}/results`, results);
  }

  completeAnalysis(id: number): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/complete-analysis`, {});
  }

  validate(id: number): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/validate`, {});
  }

  invalidate(id: number, reason: string): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}/invalidate`, JSON.stringify(reason), {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  getHistory(id: number): Observable<AuditLogDto[]> {
    return this.http.get<AuditLogDto[]>(`${this.url}/${id}/history`);
  }

  getDeadlines(id: number): Observable<DeadlineDto[]> {
    return this.http.get<DeadlineDto[]>(`${this.url}/${id}/deadlines`);
  }

  downloadPdf(id: number): Observable<Blob> {
    return this.http.get(`${this.url}/${id}/pdf`, { responseType: 'blob' });
  }

  downloadBulletin(id: number): Observable<Blob> {
    return this.http.get(`${this.url}/${id}/bulletin`, { responseType: 'blob' });
  }

  update(id: number, dto: any): Observable<RequestDetailDto> {
    return this.http.put<RequestDetailDto>(`${this.url}/${id}`, dto);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`);
  }

  setDeadlines(id: number, deadlines: any[]): Observable<any> {
    return this.http.put(`${this.url}/${id}/deadlines`, deadlines);
  }

  deleteDeadline(requestId: number, deadlineId: number): Observable<void> {
    return this.http.delete<void>(`${this.url}/${requestId}/deadlines/${deadlineId}`);
  }
}
