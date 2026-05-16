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

  deactivate(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`);
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
}
