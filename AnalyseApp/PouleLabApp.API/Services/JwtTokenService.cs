using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.IdentityModel.Tokens;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Services
{
    // Implémentation concrète du service JWT
    // Injecté partout où on a besoin de créer ou valider des tokens
    public class JwtTokenService : IJwtTokenService
    {
        // IConfiguration permet de lire les valeurs de appsettings.json et User Secrets
        private readonly IConfiguration _configuration;

        public JwtTokenService(IConfiguration configuration)
        {
            _configuration = configuration;
        }

        public string GenerateToken(ApplicationUser user, IList<string> roles)
        {
            // --- 1. Récupérer les paramètres JWT depuis la configuration ---
            // Ces valeurs viennent de appsettings.json (Issuer, Audience)
            // et de User Secrets (Secret) — jamais codées en dur
            var secret = _configuration["Jwt:Secret"]
                ?? throw new InvalidOperationException("Jwt:Secret est manquant dans la configuration.");
            var issuer = _configuration["Jwt:Issuer"]
                ?? throw new InvalidOperationException("Jwt:Issuer est manquant.");
            var audience = _configuration["Jwt:Audience"]
                ?? throw new InvalidOperationException("Jwt:Audience est manquant.");

            // --- 2. Créer la clé de signature ---
            // On convertit la clé secrète en bytes pour la cryptographie
            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
            var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

            // --- 3. Définir les Claims (informations embarquées dans le token) ---
            // Les claims sont des paires clé/valeur lisibles côté frontend et backend
            var claims = new List<Claim>
            {
                new Claim(JwtRegisteredClaimNames.Sub, user.Id),           // ID unique de l'utilisateur
                new Claim(JwtRegisteredClaimNames.Email, user.Email ?? ""), // Email
                new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()), // ID unique du token
                new Claim("firstName", user.FirstName),                    // Prénom (claim personnalisé)
                new Claim("lastName", user.LastName),                      // Nom (claim personnalisé)
                new Claim("filiale", user.FilialeName),                    // Filiale (claim personnalisé)
            };

            // Ajouter tous les rôles de l'utilisateur dans le token
            // (ex: "Admin", "Analyst") — utilisé par [Authorize(Roles="...")] côté API
            foreach (var role in roles)
            {
                claims.Add(new Claim(ClaimTypes.Role, role));
            }

            // --- 4. Créer le token JWT ---
            var token = new JwtSecurityToken(
                issuer: issuer,
                audience: audience,
                claims: claims,
                expires: DateTime.UtcNow.AddHours(2), // Le token expire après 2 heures
                signingCredentials: credentials
            );

            // --- 5. Sérialiser le token en chaîne lisible (le fameux "Bearer eyJ...") ---
            return new JwtSecurityTokenHandler().WriteToken(token);
        }

        public string GenerateRefreshToken()
        {
            // Génère 64 bytes aléatoires cryptographiquement sécurisés
            // puis les convertit en Base64 — c'est le refresh token
            var randomBytes = new byte[64];
            using var rng = RandomNumberGenerator.Create();
            rng.GetBytes(randomBytes);
            return Convert.ToBase64String(randomBytes);
        }
    }
}