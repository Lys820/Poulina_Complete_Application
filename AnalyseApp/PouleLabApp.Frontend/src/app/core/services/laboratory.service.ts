import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class LaboratoryService {
  private url = `${environment.apiUrl}/laboratories`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<any[]> {
    return this.http.get<any[]>(this.url);
  }

  create(dto: any): Observable<any> {
    return this.http.post(this.url, dto);
  }

  update(id: number, dto: any): Observable<any> {
    return this.http.put(`${this.url}/${id}`, dto);
  }

  delete(id: number): Observable<any> {
    return this.http.delete(`${this.url}/${id}`);
  }
}
