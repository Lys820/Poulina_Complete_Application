namespace PouleLabApp.API.DTOs.Auth
{
    // Réponse renvoyée au client après un login ou register réussi
    public class AuthResponseDto
    {
        public string Token { get; set; } = string.Empty;          // Le JWT à stocker côté frontend
        public string RefreshToken { get; set; } = string.Empty;   // Pour renouveler le JWT sans re-login
        public DateTime ExpiresAt { get; set; }                    // Date d'expiration du JWT
        public string UserId { get; set; } = string.Empty;         // ID de l'utilisateur connecté
        public string Email { get; set; } = string.Empty;          // Email de l'utilisateur
        public string FirstName { get; set; } = string.Empty;      // Prénom (pour affichage dans l'UI)
        public string LastName { get; set; } = string.Empty;       // Nom
        public string Role { get; set; } = string.Empty;           // Rôle principal (pour la navigation)
    }
}