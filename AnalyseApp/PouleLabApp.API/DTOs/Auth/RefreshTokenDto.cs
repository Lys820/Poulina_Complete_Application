namespace PouleLabApp.API.DTOs.Auth
{
    // Données attendues pour renouveler un JWT expiré
    public class RefreshTokenDto
    {
        public string Token { get; set; } = string.Empty;          // L'ancien JWT (même expiré)
        public string RefreshToken { get; set; } = string.Empty;   // Le refresh token valide
    }
}