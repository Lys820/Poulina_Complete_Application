using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.DTOs.Auth;
using PouleLabApp.API.DTOs.User;
using PouleLabApp.API.Models;
using PouleLabApp.API.Data;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class UserController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;
<<<<<<< HEAD
        private readonly ApplicationDbContext _context;

        public UserController(
            UserManager<ApplicationUser> userManager,
            ApplicationDbContext context)
=======
        private readonly Data.ApplicationDbContext _context;

        public UserController(
            UserManager<ApplicationUser> userManager,
            Data.ApplicationDbContext context)
>>>>>>> origin/Lilia
        {
            _userManager = userManager;
            _context     = context;
        }

        // -------------------------------------------------------
        // GET /api/user
        // -------------------------------------------------------
        [HttpGet]
        [Authorize(Policy = "RequireManager")]
        public async Task<IActionResult> GetAll()
        {
            var users = await _userManager.Users
            .Include(u => u.Laboratory) // ← ajouter
            .ToListAsync();

            var result = new List<UserDto>();
            foreach (var user in users)
            {
                var roles = await _userManager.GetRolesAsync(user);
                result.Add(new UserDto
                {
                    Id          = user.Id,
                    FirstName   = user.FirstName,
                    LastName    = user.LastName,
                    Email       = user.Email ?? "",
                    PhoneNumber = user.PhoneNumber,
                    FilialeName = user.FilialeName,
                    IsActive    = user.IsActive,
                    IsApproved = user.IsApproved,
                    CreatedAt   = user.CreatedAt,
                    Role        = roles.FirstOrDefault() ?? "Client",
                    LaboratoryId   = user.LaboratoryId,      // ← ajouter
                    LaboratoryName = user.Laboratory?.Name
                });
            }

            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/user/analysts
        // -------------------------------------------------------
        [HttpGet("analysts")]
        [Authorize(Policy = "RequireReceptionistOnly")]
        public async Task<IActionResult> GetAnalysts()
        {
            var userId = _userManager.GetUserId(User);
            var receptionist = await _userManager.FindByIdAsync(userId!);

            var analysts = await _userManager.GetUsersInRoleAsync("Analyst");
            var filtered = analysts
                .Where(u => u.IsActive)
                // ← Filtrer par labo du réceptionniste
                .Where(u => u.LaboratoryId == receptionist?.LaboratoryId)
                .Select(u => new {
                    u.Id,
                    FullName = $"{u.FirstName} {u.LastName}",
                    u.Email
                })
                .ToList();

            return Ok(filtered);
        }

        // -------------------------------------------------------
        // GET /api/user/{id}
        // -------------------------------------------------------
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(string id)
        {
            var currentUserId = _userManager.GetUserId(User);
            var isManagerOrAdmin = User.IsInRole("Administrator") || User.IsInRole("Manager");

            if (!isManagerOrAdmin && currentUserId != id)
                return Forbid();

            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            var roles = await _userManager.GetRolesAsync(user);
            return Ok(new UserDto
            {
                Id          = user.Id,
                FirstName   = user.FirstName,
                LastName    = user.LastName,
                Email       = user.Email ?? "",
                FilialeName = user.FilialeName,
                IsActive    = user.IsActive,
                CreatedAt   = user.CreatedAt,
                Role        = roles.FirstOrDefault() ?? "Client"
            });
        }

        // -------------------------------------------------------
        // POST /api/user — Admin crée un compte
        // -------------------------------------------------------
        [HttpPost]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> CreateUser([FromBody] RegisterDto dto)
        {
            var validRoles = new[] {
                "Client", "Receptionist", "Analyst", "LabChief", "Manager", "Administrator"
            };
            if (!validRoles.Contains(dto.Role))
                return BadRequest(new { message = "Rôle invalide." });

            // ← Vérifier labo obligatoire pour les rôles staff
            var staffRoles = new[] { "Receptionist", "Analyst", "LabChief" };
            if (staffRoles.Contains(dto.Role))
            {
                if (dto.LaboratoryId == null || dto.LaboratoryId == 0)
                    return BadRequest(new {
                        message = "Un laboratoire doit être assigné pour ce rôle."
                    });

                var labExists = await _context.Laboratories
                    .AnyAsync(l => l.Id == dto.LaboratoryId);
                if (!labExists)
                    return BadRequest(new { message = "Laboratoire introuvable." });
            }

            var existing = await _userManager.FindByEmailAsync(dto.Email);
            if (existing != null)
                return BadRequest(new { message = "Cet email est déjà utilisé." });

<<<<<<< HEAD
            // Filiale par défaut pour Admin/Manager
            var adminRoles = new[] { "Administrator", "Manager" };
            var filiale = adminRoles.Contains(dto.Role)
                ? "Poulina Group Holding"
                : dto.FilialeName ?? string.Empty;

            var user = new ApplicationUser
            {
                UserName     = dto.Email,
                Email        = dto.Email,
                FirstName    = dto.FirstName,
                LastName     = dto.LastName,
                PhoneNumber  = dto.PhoneNumber,
                FilialeName  = filiale,
                LaboratoryId = staffRoles.Contains(dto.Role) ? dto.LaboratoryId : null,
                IsActive     = true,
                CreatedAt    = DateTime.UtcNow
=======
            if (!string.IsNullOrEmpty(dto.PhoneNumber))
            {
                var normalizedNew = NormalizePhone(dto.PhoneNumber);
                var phoneExists = _userManager.Users
                    .AsEnumerable()
                    .Any(u => u.PhoneNumber != null
                        && NormalizePhone(u.PhoneNumber) == normalizedNew);
                if (phoneExists)
                    return BadRequest(new {
                        message = "Ce numéro de téléphone est déjà utilisé."
                    });
            }


            var user = new ApplicationUser
            {
                UserName    = dto.Email,
                Email       = dto.Email,
                FirstName   = dto.FirstName,
                LastName    = dto.LastName,
                PhoneNumber = dto.PhoneNumber,
                FilialeName = dto.FilialeName ?? string.Empty,
                LaboratoryId = dto.LaboratoryId,
                IsActive    = true,
                IsApproved = true,
                CreatedAt   = DateTime.UtcNow
>>>>>>> origin/Lilia
            };

            var result = await _userManager.CreateAsync(user, dto.Password);
            if (!result.Succeeded)
                return BadRequest(new {
                    message = string.Join(" ", result.Errors.Select(e => e.Description))
                });

            await _userManager.AddToRoleAsync(user, dto.Role);

            return Ok(new { message = $"Compte créé pour {dto.FirstName} {dto.LastName}." });
        }

        // -------------------------------------------------------
        // PUT /api/user/{id} — Admin modifie un compte
        // -------------------------------------------------------
        [HttpPut("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Update(string id, [FromBody] UpdateUserDto dto)
        {
            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            if (!string.IsNullOrEmpty(dto.PhoneNumber))
            {
                var phoneRegex = new System.Text.RegularExpressions.Regex(
                    @"^(\+216 ?)?(\d{8}|\d{2} \d{3} \d{3})$");
                if (!phoneRegex.IsMatch(dto.PhoneNumber))
                    return BadRequest(new {
                        message = "Format téléphone invalide."
                    });

                //vérifier doublon (exclure le compte modifié)
                var normalizedNew = NormalizePhone(dto.PhoneNumber);
                var phoneExists = _userManager.Users
                    .AsEnumerable() // ← nécessaire pour appliquer la normalisation côté C#
                    .Any(u => u.PhoneNumber != null
                        && NormalizePhone(u.PhoneNumber) == normalizedNew
                        && u.Id != id);
                if (phoneExists)
                    return BadRequest(new {
                        message = "Ce numéro de téléphone est déjà utilisé."
                    });
            }

            // Vérifier si le nouvel email est déjà pris par quelqu'un d'autre
            if (!string.IsNullOrEmpty(dto.Email) && dto.Email != user.Email)
            {
                var existing = await _userManager.FindByEmailAsync(dto.Email);
                if (existing != null && existing.Id != id)
                    return BadRequest(new { message = "Cet email est déjà utilisé." });

                user.Email    = dto.Email;
                user.UserName = dto.Email;
            }

            user.FirstName   = dto.FirstName;
            user.LastName    = dto.LastName;
            user.PhoneNumber = dto.PhoneNumber;
            user.FilialeName = dto.FilialeName ?? string.Empty;
            user.LaboratoryId = dto.LaboratoryId;
            user.IsActive    = dto.IsActive;

            var updateResult = await _userManager.UpdateAsync(user);
            if (!updateResult.Succeeded)
                return BadRequest(new { message = "Erreur lors de la mise à jour." });

            // Mettre à jour le rôle si nécessaire
            var currentRoles = await _userManager.GetRolesAsync(user);
            if (!currentRoles.Contains(dto.Role))
            {
                await _userManager.RemoveFromRolesAsync(user, currentRoles);
                await _userManager.AddToRoleAsync(user, dto.Role);
            }

            return Ok(new { message = "Utilisateur mis à jour avec succès." });
        }

        // -------------------------------------------------------
        // DELETE /api/user/{id} — Admin supprime un compte
        // -------------------------------------------------------
        [HttpDelete("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> DeleteUser(string id, [FromBody] PasswordConfirmDto dto)
        {
            var currentUserId = _userManager.GetUserId(User);
            if (id == currentUserId)
                return BadRequest(new {
                    message = "Vous ne pouvez pas supprimer votre propre compte."
                });

            // ← Vérifier mot de passe admin
            var admin = await _userManager.FindByIdAsync(currentUserId!);
            var passwordOk = await _userManager.CheckPasswordAsync(admin!, dto.Password);
            if (!passwordOk)
                return BadRequest(new { message = "Mot de passe incorrect." });

            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

<<<<<<< HEAD
            // ← Mettre RecordedById à null dans AnalysisResults
            var analysisResults = await _context.AnalysisResults
                .Where(r => r.RecordedById == id)
                .ToListAsync();
            foreach (var ar in analysisResults)
                ar.RecordedById = null;

            // ← Mettre PerformedById à null dans AuditLogs
            var auditLogs = await _context.AuditLogs
                .Where(a => a.PerformedById == id)
                .ToListAsync();
            foreach (var log in auditLogs)
                log.PerformedById = null;

            // ← Mettre AssignedToId à null dans AnalysisRequests
            var assignedRequests = await _context.AnalysisRequests
                .Where(r => r.AssignedToId == id)
                .ToListAsync();
            foreach (var req in assignedRequests)
                req.AssignedToId = null;

            // ← Supprimer les notifications de cet utilisateur
            var notifications = await _context.Notifications
                .Where(n => n.RecipientId == id)
                .ToListAsync();
            _context.Notifications.RemoveRange(notifications);

            // ← Supprimer toutes les demandes dont l'utilisateur est le client
            var clientRequests = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .Include(r => r.Deadlines)
                .Include(r => r.AuditLogs)
                .Include(r => r.Notifications)
                .Where(r => r.ClientId == id)
                .ToListAsync();
=======
            // Nettoyer les FK
            var analysisResults = await _context.AnalysisResults
                .Where(r => r.RecordedById == id).ToListAsync();
            foreach (var ar in analysisResults) ar.RecordedById = null;

            var auditLogs = await _context.AuditLogs
                .Where(a => a.PerformedById == id).ToListAsync();
            foreach (var log in auditLogs) log.PerformedById = null;

            var assignedRequests = await _context.AnalysisRequests
                .Where(r => r.AssignedToId == id).ToListAsync();
            foreach (var req in assignedRequests) req.AssignedToId = null;

            var notifications = await _context.Notifications
                .Where(n => n.RecipientId == id).ToListAsync();
            _context.Notifications.RemoveRange(notifications);

            var clientRequests = await _context.AnalysisRequests
                .Include(r => r.Samples).ThenInclude(s => s.Results)
                .Include(r => r.Deadlines)
                .Include(r => r.AuditLogs)
                .Include(r => r.Notifications)
                .Where(r => r.ClientId == id).ToListAsync();
>>>>>>> origin/Lilia

            foreach (var req in clientRequests)
            {
                _context.AnalysisResults.RemoveRange(
                    req.Samples.SelectMany(s => s.Results));
                _context.Deadlines.RemoveRange(req.Deadlines);
                _context.Samples.RemoveRange(req.Samples);
                _context.AuditLogs.RemoveRange(req.AuditLogs);
                _context.Notifications.RemoveRange(req.Notifications);
                _context.AnalysisRequests.Remove(req);
            }

            await _context.SaveChangesAsync();

            var result = await _userManager.DeleteAsync(user);
            if (!result.Succeeded)
                return BadRequest(new {
                    message = string.Join(" ", result.Errors.Select(e => e.Description))
                });

            return Ok(new {
                message = $"Compte de {user.FirstName} {user.LastName} supprimé."
            });
        }

        // -------------------------------------------------------
        // PATCH /api/user/{id}/status — Activer ou désactiver
        // -------------------------------------------------------
        [HttpPatch("{id}/status")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> ToggleStatus(string id, [FromBody] PasswordConfirmDto dto)
        {
            var currentUserId = _userManager.GetUserId(User);

            // ← Vérifier mot de passe admin
            var admin = await _userManager.FindByIdAsync(currentUserId!);
            var passwordOk = await _userManager.CheckPasswordAsync(admin!, dto.Password);
            if (!passwordOk)
                return BadRequest(new { message = "Mot de passe incorrect." });
            
            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            user.IsActive = !user.IsActive;
            await _userManager.UpdateAsync(user);

            var status = user.IsActive ? "activé" : "désactivé";
            return Ok(new { message = $"Compte {status} avec succès." });
        }

        // -------------------------------------------------------
        // GET /api/user/me — Récupérer son propre profil
        // -------------------------------------------------------
        [HttpGet("me")]
        public async Task<IActionResult> GetMyProfile()
        {
            var userId = _userManager.GetUserId(User);
            var user   = await _userManager.FindByIdAsync(userId!);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            var roles = await _userManager.GetRolesAsync(user);
            return Ok(new UserDto
            {
                Id          = user.Id,
                FirstName   = user.FirstName,
                LastName    = user.LastName,
                Email       = user.Email ?? "",
                FilialeName = user.FilialeName,
                PhoneNumber = user.PhoneNumber ?? "",
                IsActive    = user.IsActive,
                CreatedAt   = user.CreatedAt,
                Role        = roles.FirstOrDefault() ?? "Client"
            });
        }

        // -------------------------------------------------------
        // PUT /api/user/me — Modifier son propre profil
        // -------------------------------------------------------
        [HttpPut("me")]
        public async Task<IActionResult> UpdateMyProfile([FromBody] UpdateProfileDto dto)
        {
            var userId = _userManager.GetUserId(User);
            var user   = await _userManager.FindByIdAsync(userId!);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            if (!string.IsNullOrEmpty(dto.PhoneNumber))
            {
                var phoneRegex = new System.Text.RegularExpressions.Regex(
                    @"^(\+216 ?)?(\d{8}|\d{2} \d{3} \d{3})$");
                if (!phoneRegex.IsMatch(dto.PhoneNumber))
                    return BadRequest(new {
                        message = "Format téléphone invalide."
                    });

                // Vérifier doublon (exclure le compte actuel)
                var normalizedNew = NormalizePhone(dto.PhoneNumber);
                var phoneExists = _userManager.Users
                    .AsEnumerable()
                    .Any(u => u.PhoneNumber != null
                        && NormalizePhone(u.PhoneNumber) == normalizedNew
                        && u.Id != userId);
                if (phoneExists)
                    return BadRequest(new {
                        message = "Ce numéro de téléphone est déjà utilisé."
                    });
            }
            
            user.FirstName   = dto.FirstName;
            user.LastName    = dto.LastName;
            user.PhoneNumber = dto.PhoneNumber;
            user.FilialeName = dto.FilialeName ?? string.Empty;

            // Changement de mot de passe optionnel
            if (!string.IsNullOrEmpty(dto.NewPassword))
            {
                if (string.IsNullOrEmpty(dto.CurrentPassword))
                    return BadRequest(new {
                        message = "Le mot de passe actuel est requis."
                    });

                var passwordResult = await _userManager.ChangePasswordAsync(
                    user, dto.CurrentPassword, dto.NewPassword);

                if (!passwordResult.Succeeded)
                    return BadRequest(new {
                        message = string.Join(" ",
                            passwordResult.Errors.Select(e => e.Description))
                    });
            }

            var result = await _userManager.UpdateAsync(user);
            if (!result.Succeeded)
                return BadRequest(new { message = "Erreur lors de la mise à jour." });

            return Ok(new { message = "Profil mis à jour avec succès." });
        }

        // -------------------------------------------------------
        // DELETE /api/user/me — Supprimer son propre compte
        // -------------------------------------------------------
        [HttpPost("me/delete")]
        public async Task<IActionResult> DeleteMyAccount([FromBody] PasswordConfirmDto dto)
        {
            var userId = _userManager.GetUserId(User);
            var user   = await _userManager.FindByIdAsync(userId!);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            // Vérifier le mot de passe
            var passwordOk = await _userManager.CheckPasswordAsync(user, dto.Password);
            if (!passwordOk)
             return BadRequest(new { message = "Mot de passe incorrect." });
           
            // Nettoyer les FK
            var analysisResults = await _context.AnalysisResults
                .Where(r => r.RecordedById == userId).ToListAsync();
            foreach (var ar in analysisResults) ar.RecordedById = null;

            var auditLogs = await _context.AuditLogs
                .Where(a => a.PerformedById == userId).ToListAsync();
            foreach (var log in auditLogs) log.PerformedById = null;

            var assignedRequests = await _context.AnalysisRequests
                .Where(r => r.AssignedToId == userId).ToListAsync();
            foreach (var req in assignedRequests) req.AssignedToId = null;

            var notifications = await _context.Notifications
                .Where(n => n.RecipientId == userId).ToListAsync();
            _context.Notifications.RemoveRange(notifications);

            var clientRequests = await _context.AnalysisRequests
                .Include(r => r.Samples).ThenInclude(s => s.Results)
                .Include(r => r.Deadlines)
                .Include(r => r.AuditLogs)
                .Include(r => r.Notifications)
                .Where(r => r.ClientId == userId).ToListAsync();

            foreach (var req in clientRequests)
            {
                _context.AnalysisResults.RemoveRange(
                    req.Samples.SelectMany(s => s.Results));
                _context.Deadlines.RemoveRange(req.Deadlines);
                _context.Samples.RemoveRange(req.Samples);
                _context.AuditLogs.RemoveRange(req.AuditLogs);
                _context.Notifications.RemoveRange(req.Notifications);
                _context.AnalysisRequests.Remove(req);
            }

            await _context.SaveChangesAsync();

            var result = await _userManager.DeleteAsync(user);
            if (!result.Succeeded)
                return BadRequest(new {
                    message = string.Join(" ", result.Errors.Select(e => e.Description))
                });

            return Ok(new { message = "Compte supprimé avec succès." });
        }

        [HttpPost("{id}/approve")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> ApproveUser(string id)
        {
            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            user.IsActive = true;
            user.IsApproved = true;
            await _userManager.UpdateAsync(user);

            return Ok(new {
                message = $"Compte de {user.FirstName} {user.LastName} approuvé."
            });
        }

        private static string NormalizePhone(string phone)
        {
            // Supprimer tous les espaces
            var cleaned = phone.Replace(" ", "");
            // Supprimer le préfixe +216 si présent
            if (cleaned.StartsWith("+216"))
                cleaned = cleaned.Substring(4);
            return cleaned;
        }
    }

}