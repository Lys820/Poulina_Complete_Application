namespace PouleLabApp.API.DTOs.Auth
{
    // Données attendues dans le body de la requête POST /api/auth/register
    public class RegisterDto
    {
        public string FirstName { get; set; } = string.Empty;      // Prénom obligatoire
        public string LastName { get; set; } = string.Empty;       // Nom obligatoire
        public string Email { get; set; } = string.Empty;          // Email = identifiant de connexion
        public string Password { get; set; } = string.Empty;       // Mot de passe (sera hashé)
        public string FilialeName { get; set; } = string.Empty;    // Filiale de l'utilisateur
        public string Role { get; set; } = "Client";               // Rôle par défaut si non précisé
    }
}