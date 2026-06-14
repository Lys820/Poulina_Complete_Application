namespace PouleLabApp.API.Models
{
    /// <summary>
    /// Poultry breed recommended by the ML chatbot.
    /// Seeded at startup via DataSeeder.
    /// </summary>
    public class Breed
    {
        public int      Id             { get; set; }
        public string   Name           { get; set; } = string.Empty;
        public string   ProductionType { get; set; } = string.Empty; // "Broiler", "Layer", "Turkey"
        public string   Origin         { get; set; } = string.Empty;
        public string   Description    { get; set; } = string.Empty;
        public double   AverageScore   { get; set; }
        public bool     IsActive       { get; set; } = true;
        public DateTime CreatedAt      { get; set; } = DateTime.UtcNow;
    }
}