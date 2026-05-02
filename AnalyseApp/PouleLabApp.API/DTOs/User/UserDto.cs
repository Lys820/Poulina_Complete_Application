namespace PouleLabApp.API.DTOs.User
{
    // DTO de lecture — ce qu'on renvoie quand on consulte un utilisateur
    // On ne renvoie jamais le mot de passe ni les champs internes d'Identity
    public class UserDto
    {
        public string Id { get; set; } = string.Empty;
        public string FirstName { get; set; } = string.Empty;
        public string LastName { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public string FilialeName { get; set; } = string.Empty;
        public bool IsActive { get; set; }
        public DateTime CreatedAt { get; set; }
        public string Role { get; set; } = string.Empty;  // Rôle principal de l'utilisateur
    }
}