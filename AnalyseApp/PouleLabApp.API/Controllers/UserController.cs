using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.DTOs.Auth;
using PouleLabApp.API.DTOs.User;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class UserController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;

        public UserController(UserManager<ApplicationUser> userManager)
        {
            _userManager = userManager;
        }

        // -------------------------------------------------------
        // GET /api/user
        // -------------------------------------------------------
        [HttpGet]
        [Authorize(Policy = "RequireManager")]
        public async Task<IActionResult> GetAll()
        {
            var users = await _userManager.Users.ToListAsync();

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
                    CreatedAt   = user.CreatedAt,
                    Role        = roles.FirstOrDefault() ?? "Client"
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
            var analysts = await _userManager.GetUsersInRoleAsync("Analyst");
            var activeAnalysts = analysts
                .Where(u => u.IsActive)
                .Select(u => new {
                    u.Id,
                    FullName = $"{u.FirstName} {u.LastName}",
                    u.Email
                })
                .ToList();

            return Ok(activeAnalysts);
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

            var existing = await _userManager.FindByEmailAsync(dto.Email);
            if (existing != null)
                return BadRequest(new { message = "Cet email est déjà utilisé." });

            var user = new ApplicationUser
            {
                UserName    = dto.Email,
                Email       = dto.Email,
                FirstName   = dto.FirstName,
                LastName    = dto.LastName,
                PhoneNumber = dto.PhoneNumber,
                FilialeName = dto.FilialeName ?? string.Empty,
                IsActive    = true,
                CreatedAt   = DateTime.UtcNow
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
        public async Task<IActionResult> DeleteUser(string id)
        {
            var currentUserId = _userManager.GetUserId(User);
            if (id == currentUserId)
                return BadRequest(new {
                    message = "Vous ne pouvez pas supprimer votre propre compte."
                });

            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

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
        public async Task<IActionResult> ToggleStatus(string id)
        {
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
        [HttpDelete("me")]
        public async Task<IActionResult> DeleteMyAccount()
        {
            var userId = _userManager.GetUserId(User);
            var user   = await _userManager.FindByIdAsync(userId!);
            if (user == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            var result = await _userManager.DeleteAsync(user);
            if (!result.Succeeded)
                return BadRequest(new {
                    message = string.Join(" ",
                        result.Errors.Select(e => e.Description))
                });

            return Ok(new { message = "Compte supprimé avec succès." });
        }
    }
}