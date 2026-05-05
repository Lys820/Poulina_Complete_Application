using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize] // JWT obligatoire pour tous les endpoints
    public class RoleController : ControllerBase
    {
        private readonly RoleManager<IdentityRole> _roleManager;
        private readonly UserManager<ApplicationUser> _userManager;

        public RoleController(
            RoleManager<IdentityRole> roleManager,
            UserManager<ApplicationUser> userManager)
        {
            _roleManager = roleManager;
            _userManager = userManager;
        }

        // -------------------------------------------------------
        // GET /api/role
        // Retourne la liste de tous les rôles disponibles
        // Accessible à tous les utilisateurs connectés
        // -------------------------------------------------------
        [HttpGet]
        public IActionResult GetAll()
        {
            // Récupérer tous les rôles enregistrés en base par le Seeder
            var roles = _roleManager.Roles
                .Select(r => new { r.Id, r.Name })
                .ToList();

            return Ok(roles);
        }

        // -------------------------------------------------------
        // POST /api/role/assign/{userId}
        // Assigne un rôle à un utilisateur
        // Accessible aux Admins uniquement
        // -------------------------------------------------------
        [HttpPost("assign/{userId}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> AssignRole(string userId, [FromBody] string roleName)
        {
            // Vérifier que l'utilisateur existe
            var user = await _userManager.FindByIdAsync(userId);
            if (user == null)
            {
                return NotFound(new { message = "Utilisateur introuvable." });
            }

            // Vérifier que le rôle existe
            var roleExists = await _roleManager.RoleExistsAsync(roleName);
            if (!roleExists)
            {
                return BadRequest(new { message = $"Le rôle '{roleName}' n'existe pas." });
            }

            // Supprimer les anciens rôles avant d'assigner le nouveau
            // Un utilisateur n'a qu'un seul rôle à la fois dans cette application
            var currentRoles = await _userManager.GetRolesAsync(user);
            await _userManager.RemoveFromRolesAsync(user, currentRoles);

            // Assigner le nouveau rôle
            var result = await _userManager.AddToRoleAsync(user, roleName);
            if (!result.Succeeded)
            {
                return BadRequest(new { message = "Erreur lors de l'assignation du rôle." });
            }

            return Ok(new { message = $"Rôle '{roleName}' assigné à {user.Email} avec succès." });
        }

        // -------------------------------------------------------
        // GET /api/role/user/{userId}
        // Retourne le rôle d'un utilisateur spécifique
        // Accessible aux Admins et Managers
        // -------------------------------------------------------
        [HttpGet("user/{userId}")]
        [Authorize(Policy = "RequireManager")]
        public async Task<IActionResult> GetUserRole(string userId)
        {
            var user = await _userManager.FindByIdAsync(userId);
            if (user == null)
            {
                return NotFound(new { message = "Utilisateur introuvable." });
            }

            var roles = await _userManager.GetRolesAsync(user);

            return Ok(new
            {
                userId = user.Id,
                email = user.Email,
                roles = roles
            });
        }
    }
}