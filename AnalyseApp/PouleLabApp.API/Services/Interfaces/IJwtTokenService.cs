using PouleLabApp.API.Models;

namespace PouleLabApp.API.Services.Interfaces
{
    // Contrat que tout service de génération de tokens JWT doit respecter
    public interface IJwtTokenService
    {
        // Génère un token JWT signé pour un utilisateur avec ses rôles
        string GenerateToken(ApplicationUser user, IList<string> roles);

        // Génère un refresh token aléatoire sécurisé (utilisé pour renouveler le JWT sans re-login)
        string GenerateRefreshToken();
    }
}