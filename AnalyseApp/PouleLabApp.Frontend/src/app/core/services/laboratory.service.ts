import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class LaboratoryService {
  private url = `${environment.apiUrl}/laboratories`;

  constructor(private http: HttpClient) {}

<<<<<<< HEAD
  getAll(): Observable<any[]> {
    return this.http.get<any[]>(this.url);
=======
  // ← Alias utilisé par les formulaires d'inscription
  getLaboratories(): Observable<Laboratory[]> {
    return this.http.get<Laboratory[]>(this.url);
  }

  // ← CRUD complet pour la gestion admin
  getAll(): Observable<any[]> {
    return this.http.get<any[]>(this.url);
  }

  getById(id: number): Observable<any> {
    return this.http.get<any>(`${this.url}/${id}`);
  }

  create(dto: any): Observable<any> {
    return this.http.post<any>(this.url, dto);
  }

  update(id: number, dto: any): Observable<any> {
    return this.http.put<any>(`${this.url}/${id}`, dto);
  }

  delete(id: number): Observable<any> {
    return this.http.delete<any>(`${this.url}/${id}`);
>>>>>>> origin/Lilia
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
