namespace PouleLabApp.API.DTOs.Auth
{
    // Données attendues dans le body de la requête POST /api/auth/login
    public class LoginDto
    {
        public string Email { get; set; } = string.Empty;      // Identifiant
        public string Password { get; set; } = string.Empty;   // Mot de passe en clair (jamais stocké tel quel)
    }
}