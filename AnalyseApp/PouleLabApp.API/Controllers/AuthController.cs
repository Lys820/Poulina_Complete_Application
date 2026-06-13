using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.DTOs.Auth;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;
using PouleLabApp.API.DTOs;
using Microsoft.AspNetCore.Authorization;

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

        private readonly Data.ApplicationDbContext _context;

        // Injection de dépendances via le constructeur
        public AuthController(
            UserManager<ApplicationUser> userManager,
            SignInManager<ApplicationUser> signInManager,
            IJwtTokenService jwtTokenService,
            Data.ApplicationDbContext context) // ← ajouter
        {
            _userManager     = userManager;
            _signInManager   = signInManager;
            _jwtTokenService = jwtTokenService;
            _context         = context;        // ← ajouter
        }

        // -------------------------------------------------------
        // POST /api/auth/register
        // Crée un nouveau compte utilisateur
        // -------------------------------------------------------
        [HttpPost("register")]
        [AllowAnonymous]
        public async Task<IActionResult> Register([FromBody] RegisterDto dto)
        {
            // Vérifier que le rôle est valide
            var validRoles = new[] {
                "Client", "Receptionist", "Analyst", "LabChief", "Manager", "Administrator"
            };
            if (!validRoles.Contains(dto.Role))
                return BadRequest(new { message = "Rôle invalide." });

            // Vérifier si l'email existe déjà
            var existing = await _userManager.FindByEmailAsync(dto.Email);
            if (existing != null)
                return BadRequest(new { message = "Cet email est déjà utilisé." });

            //Vérifier si le numéro de téléphone existe déjà
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
                IsActive    = false, // ← inactif jusqu'à validation admin
                CreatedAt   = DateTime.UtcNow
            };

            var result = await _userManager.CreateAsync(user, dto.Password);
            if (!result.Succeeded)
            {
                var errors = result.Errors.Select(e => e.Description);
                return BadRequest(new { message = string.Join(" ", errors) });
            }

            await _userManager.AddToRoleAsync(user, dto.Role);

            // ← Notifier tous les admins du nouveau compte en attente
            var admins = await _userManager.GetUsersInRoleAsync("Administrator");
            foreach (var admin in admins)
            {
                _context.Notifications.Add(new Notification
                {
                    RecipientId = admin.Id,
                    RequestId   = null, // ← pas lié à une demande
                    Message     = $"Nouveau compte en attente de validation : " +
                                $"{user.FirstName} {user.LastName} ({dto.Role}).",
                    IsRead      = false,
                    CreatedAt   = DateTime.UtcNow
                });
            }
            await _context.SaveChangesAsync();

            return Ok(new { message = "Compte créé avec succès. En attente de validation par un administrateur." });

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

            if (!user.IsActive)
            {
                return Unauthorized(new {
                    message = "Votre compte est en attente de validation par un administrateur."
                });
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