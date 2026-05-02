using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.DTOs.Auth;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;
using PouleLabApp.API.DTOs;

namespace PouleLabApp.API.Controllers
{
    // [ApiController] active la validation automatique des DTOs et les réponses JSON
    // [Route] définit le préfixe de tous les endpoints de ce controller : /api/auth/...
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {
        // UserManager : gère la création, recherche et modification des utilisateurs (fourni par Identity)
        private readonly UserManager<ApplicationUser> _userManager;

        // SignInManager : gère la vérification des credentials (email + mot de passe)
        private readonly SignInManager<ApplicationUser> _signInManager;

        // Notre service JWT pour générer les tokens
        private readonly IJwtTokenService _jwtTokenService;

        // Injection de dépendances via le constructeur
        public AuthController(
            UserManager<ApplicationUser> userManager,
            SignInManager<ApplicationUser> signInManager,
            IJwtTokenService jwtTokenService)
        {
            _userManager = userManager;
            _signInManager = signInManager;
            _jwtTokenService = jwtTokenService;
        }

        // -------------------------------------------------------
        // POST /api/auth/register
        // Crée un nouveau compte utilisateur
        // -------------------------------------------------------
        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegisterDto dto)
        {
            // Vérifier si l'email est déjà utilisé
            var existingUser = await _userManager.FindByEmailAsync(dto.Email);
            if (existingUser != null)
            {
                // 400 Bad Request avec message d'erreur explicite
                return BadRequest(new { message = "Un compte avec cet email existe déjà." });
            }

            // Créer l'objet utilisateur à partir du DTO
            var user = new ApplicationUser
            {
                UserName = dto.Email,           // Identity utilise UserName comme identifiant
                Email = dto.Email,
                FirstName = dto.FirstName,
                LastName = dto.LastName,
                FilialeName = dto.FilialeName,
                IsActive = true,
                CreatedAt = DateTime.UtcNow
            };

            // Identity hash automatiquement le mot de passe — on ne le stocke jamais en clair
            var result = await _userManager.CreateAsync(user, dto.Password);

            if (!result.Succeeded)
            {
                // Retourner toutes les erreurs de validation Identity (ex: mot de passe trop court)
                var errors = result.Errors.Select(e => e.Description);
                return BadRequest(new { message = "Erreur lors de la création du compte.", errors });
            }

            // Vérifier que le rôle demandé est valide, sinon utiliser "Client" par défaut
            var validRoles = new[] { "Administrator", "Manager", "Receptionist", "Analyst", "LabChief", "Client" };
            var roleToAssign = validRoles.Contains(dto.Role) ? dto.Role : "Client";

            // Assigner le rôle à l'utilisateur
            await _userManager.AddToRoleAsync(user, roleToAssign);

            // Générer le JWT et le refresh token immédiatement après l'inscription
            var roles = await _userManager.GetRolesAsync(user);
            var token = _jwtTokenService.GenerateToken(user, roles);
            var refreshToken = _jwtTokenService.GenerateRefreshToken();

            // 201 Created avec le token dans la réponse
            return StatusCode(201, new AuthResponseDto
            {
                Token = token,
                RefreshToken = refreshToken,
                ExpiresAt = DateTime.UtcNow.AddHours(2),
                UserId = user.Id,
                Email = user.Email!,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Role = roleToAssign
            });
        }

        // -------------------------------------------------------
        // POST /api/auth/login
        // Authentifie un utilisateur et retourne un JWT
        // -------------------------------------------------------
        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginDto dto)
        {
            // Chercher l'utilisateur par email
            var user = await _userManager.FindByEmailAsync(dto.Email);
            if (user == null)
            {
                // Message volontairement vague pour ne pas révéler si l'email existe ou non
                return Unauthorized(new { message = "Email ou mot de passe incorrect." });
            }

            // Vérifier que le compte est actif
            if (!user.IsActive)
            {
                return Unauthorized(new { message = "Ce compte a été désactivé. Contactez un administrateur." });
            }

            // Vérifier le mot de passe — Identity compare avec le hash stocké en base
            // false = ne pas verrouiller le compte après plusieurs tentatives échouées
            var result = await _signInManager.CheckPasswordSignInAsync(user, dto.Password, false);
            if (!result.Succeeded)
            {
                return Unauthorized(new { message = "Email ou mot de passe incorrect." });
            }

            // Récupérer les rôles pour les embarquer dans le token
            var roles = await _userManager.GetRolesAsync(user);
            var token = _jwtTokenService.GenerateToken(user, roles);
            var refreshToken = _jwtTokenService.GenerateRefreshToken();

            // 200 OK avec le token
            return Ok(new AuthResponseDto
            {
                Token = token,
                RefreshToken = refreshToken,
                ExpiresAt = DateTime.UtcNow.AddHours(2),
                UserId = user.Id,
                Email = user.Email!,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Role = roles.FirstOrDefault() ?? "Client"
            });
        }

        // -------------------------------------------------------
        // POST /api/auth/refresh
        // Renouvelle un JWT expiré grâce au refresh token
        // -------------------------------------------------------
        [HttpPost("refresh")]
        public async Task<IActionResult> Refresh([FromBody] RefreshTokenDto dto)
        {
            // Note : dans une vraie application en production, on stockerait
            // les refresh tokens en base de données pour pouvoir les révoquer.
            // Pour ce projet, on valide juste que le token JWT est bien formé
            // et on génère un nouveau JWT pour l'utilisateur correspondant.

            // Extraire l'ID utilisateur du JWT (même expiré)
            var tokenHandler = new System.IdentityModel.Tokens.Jwt.JwtSecurityTokenHandler();

            System.IdentityModel.Tokens.Jwt.JwtSecurityToken? jwtToken;
            try
            {
                // Lire le token sans valider l'expiration pour extraire les claims
                jwtToken = tokenHandler.ReadJwtToken(dto.Token);
            }
            catch
            {
                return BadRequest(new { message = "Token invalide." });
            }

            // Récupérer l'ID utilisateur depuis les claims du token
            var userId = jwtToken.Claims
                .FirstOrDefault(c => c.Type == System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Sub)
                ?.Value;

            if (userId == null)
            {
                return BadRequest(new { message = "Token invalide : utilisateur introuvable." });
            }

            // Chercher l'utilisateur en base
            var user = await _userManager.FindByIdAsync(userId);
            if (user == null || !user.IsActive)
            {
                return Unauthorized(new { message = "Utilisateur introuvable ou inactif." });
            }

            // Générer un nouveau JWT valide
            var roles = await _userManager.GetRolesAsync(user);
            var newToken = _jwtTokenService.GenerateToken(user, roles);
            var newRefreshToken = _jwtTokenService.GenerateRefreshToken();

            return Ok(new AuthResponseDto
            {
                Token = newToken,
                RefreshToken = newRefreshToken,
                ExpiresAt = DateTime.UtcNow.AddHours(2),
                UserId = user.Id,
                Email = user.Email!,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Role = roles.FirstOrDefault() ?? "Client"
            });
        }
    }
}