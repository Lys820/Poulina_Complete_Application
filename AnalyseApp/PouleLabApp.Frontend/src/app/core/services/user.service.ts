import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { UserDto, UpdateUserDto, AnalystDto } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private url = `${environment.apiUrl}/user`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<UserDto[]> {
    return this.http.get<UserDto[]>(this.url);
  }

  getById(id: string): Observable<UserDto> {
    return this.http.get<UserDto>(`${this.url}/${id}`);
  }

  update(id: string, dto: UpdateUserDto): Observable<void> {
    return this.http.put<void>(`${this.url}/${id}`, dto);
  }

  // Activer/désactiver un compte
  toggleStatus(id: string): Observable<any> {
    return this.http.patch(`${this.url}/${id}/status`, {});
  }

  getRoles(): Observable<{ id: string; name: string }[]> {
    return this.http.get<{ id: string; name: string }[]>(`${environment.apiUrl}/role`);
  }

  assignRole(userId: string, role: string): Observable<void> {
    return this.http.post<void>(
      `${environment.apiUrl}/role/assign/${userId}`,
      JSON.stringify(role),
      { headers: { 'Content-Type': 'application/json' } },
    );
  }

  getAnalysts(): Observable<AnalystDto[]> {
    return this.http.get<AnalystDto[]>(`${this.url}/analysts`);
  }

  createUser(dto: any): Observable<any> {
    return this.http.post(`${this.url}`, dto);
  }

  deleteUser(id: string): Observable<any> {
    return this.http.delete(`${this.url}/${id}`);
  }

  getMyProfile(): Observable<any> {
    return this.http.get(`${this.url}/me`);
  }

  updateMyProfile(dto: any): Observable<any> {
    return this.http.put(`${this.url}/me`, dto);
  }

  deleteMyAccount(): Observable<any> {
    return this.http.delete(`${this.url}/me`);
  }

  getLaboratories(): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/laboratories`);
  }

  approveUser(id: string): Observable<any> {
    return this.http.post(`${this.url}/${id}/approve`, {});
  }
}
