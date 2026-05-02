namespace PouleLabApp.API.DTOs.User
{
    // DTO de modification — seuls ces champs peuvent être modifiés
    // On ne permet pas de changer l'email (identifiant) ni le mot de passe ici
    public class UpdateUserDto
    {
        public string FirstName { get; set; } = string.Empty;
        public string LastName { get; set; } = string.Empty;
        public string FilialeName { get; set; } = string.Empty;
        public bool IsActive { get; set; }
        public string Role { get; set; } = string.Empty;
    }
}