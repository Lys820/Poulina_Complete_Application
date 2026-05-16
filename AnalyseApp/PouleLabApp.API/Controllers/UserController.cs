using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.DTOs.User;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize] // Tous les endpoints de ce controller nécessitent un JWT valide
    public class UserController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;

        public UserController(UserManager<ApplicationUser> userManager)
        {
            _userManager = userManager;
        }

        // -------------------------------------------------------
        // GET /api/user
        // Retourne la liste de tous les utilisateurs
        // Accessible uniquement aux Admins et Managers
        // -------------------------------------------------------
        [HttpGet]
        [Authorize(Policy = "RequireManager")]
        public async Task<IActionResult> GetAll()
        {
            // Récupérer tous les utilisateurs depuis la base
            var users = await _userManager.Users.ToListAsync();

            // Construire la liste de DTOs avec le rôle de chaque utilisateur
            var result = new List<UserDto>();
            foreach (var user in users)
            {
                var roles = await _userManager.GetRolesAsync(user);
                result.Add(new UserDto
                {
                    Id = user.Id,
                    FirstName = user.FirstName,
                    LastName = user.LastName,
                    Email = user.Email ?? "",
                    FilialeName = user.FilialeName,
                    IsActive = user.IsActive,
                    CreatedAt = user.CreatedAt,
                    Role = roles.FirstOrDefault() ?? "Client"
                });
            }

            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/user/{id}
        // Retourne les détails d'un utilisateur spécifique
        // Accessible aux Admins, Managers, et à l'utilisateur lui-même
        // -------------------------------------------------------
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(string id)
        {
            // Récupérer l'ID de l'utilisateur connecté depuis le JWT
            var currentUserId = _userManager.GetUserId(User);

            // Vérifier les droits : Admin/Manager OU l'utilisateur lui-même
            var isManagerOrAdmin = User.IsInRole("Administrator") || User.IsInRole("Manager");
            if (!isManagerOrAdmin && currentUserId != id)
            {
                return Forbid(); // 403 Forbidden
            }

            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
            {
                return NotFound(new { message = "Utilisateur introuvable." });
            }

            var roles = await _userManager.GetRolesAsync(user);
            return Ok(new UserDto
            {
                Id = user.Id,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Email = user.Email ?? "",
                FilialeName = user.FilialeName,
                IsActive = user.IsActive,
                CreatedAt = user.CreatedAt,
                Role = roles.FirstOrDefault() ?? "Client"
            });
        }

        // -------------------------------------------------------
        // PUT /api/user/{id}
        // Modifie les informations d'un utilisateur
        // Accessible aux Admins uniquement
        // -------------------------------------------------------
        [HttpPut("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Update(string id, [FromBody] UpdateUserDto dto)
        {
            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
            {
                return NotFound(new { message = "Utilisateur introuvable." });
            }

            // Mettre à jour les champs modifiables
            user.FirstName = dto.FirstName;
            user.LastName = dto.LastName;
            user.FilialeName = dto.FilialeName;
            user.IsActive = dto.IsActive;

            var updateResult = await _userManager.UpdateAsync(user);
            if (!updateResult.Succeeded)
            {
                return BadRequest(new { message = "Erreur lors de la mise à jour." });
            }

            // Mettre à jour le rôle si nécessaire
            var currentRoles = await _userManager.GetRolesAsync(user);
            if (!currentRoles.Contains(dto.Role))
            {
                // Supprimer tous les anciens rôles puis assigner le nouveau
                await _userManager.RemoveFromRolesAsync(user, currentRoles);
                await _userManager.AddToRoleAsync(user, dto.Role);
            }

            return Ok(new { message = "Utilisateur mis à jour avec succès." });
        }

        // -------------------------------------------------------
        // DELETE /api/user/{id}
        // Désactive un utilisateur (soft delete — on ne supprime jamais en base)
        // Accessible aux Admins uniquement
        // -------------------------------------------------------
        [HttpDelete("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Deactivate(string id)
        {
            var user = await _userManager.FindByIdAsync(id);
            if (user == null)
            {
                return NotFound(new { message = "Utilisateur introuvable." });
            }

            // Soft delete : on désactive le compte sans le supprimer de la base
            // Cela préserve l'historique et la traçabilité des actions passées
            user.IsActive = false;
            await _userManager.UpdateAsync(user);

            return Ok(new { message = "Utilisateur désactivé avec succès." });
        }

        // GET /api/user/analysts — liste uniquement les laborantins actifs
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
    }
}