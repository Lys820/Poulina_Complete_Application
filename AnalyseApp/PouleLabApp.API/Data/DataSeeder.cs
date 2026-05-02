using Microsoft.AspNetCore.Identity;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Data
{
    // Remplit la base de données avec les données initiales indispensables au fonctionnement
    // Appelé une seule fois au démarrage de l'application via Program.cs
    public static class DataSeeder
    {
        public static async Task SeedAsync(
            RoleManager<IdentityRole> roleManager,
            UserManager<ApplicationUser> userManager)
        {
            // -------------------------------------------------------
            // 1. CRÉER LES RÔLES
            // On crée chaque rôle s'il n'existe pas déjà en base
            // -------------------------------------------------------
            var roles = new[]
            {
                "Administrator",
                "Manager",
                "Receptionist",
                "Analyst",
                "LabChief",
                "Client"
            };

            foreach (var role in roles)
            {
                // RoleExistsAsync vérifie en base avant de créer pour éviter les doublons
                if (!await roleManager.RoleExistsAsync(role))
                {
                    await roleManager.CreateAsync(new IdentityRole(role));
                    Console.WriteLine($"[Seeder] Rôle créé : {role}");
                }
            }

            // -------------------------------------------------------
            // 2. CRÉER LE COMPTE ADMINISTRATEUR INITIAL
            // Ce compte permet de se connecter la première fois
            // et de créer les autres utilisateurs via l'API
            // -------------------------------------------------------
            const string adminEmail = "admin@poulelabapp.com";
            const string adminPassword = "Admin@1234";

            // Vérifier si l'admin existe déjà avant de le créer
            var existingAdmin = await userManager.FindByEmailAsync(adminEmail);
            if (existingAdmin == null)
            {
                var admin = new ApplicationUser
                {
                    UserName = adminEmail,
                    Email = adminEmail,
                    FirstName = "Super",
                    LastName = "Admin",
                    FilialeName = "Poulina Group Holding",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow,
                    EmailConfirmed = true // On confirme l'email directement pour éviter les blocages
                };

                // Identity hash automatiquement le mot de passe
                var result = await userManager.CreateAsync(admin, adminPassword);

                if (result.Succeeded)
                {
                    // Assigner le rôle Administrator au compte admin
                    await userManager.AddToRoleAsync(admin, "Administrator");
                    Console.WriteLine($"[Seeder] Compte admin créé : {adminEmail}");
                }
                else
                {
                    // Afficher les erreurs si la création échoue
                    foreach (var error in result.Errors)
                    {
                        Console.WriteLine($"[Seeder] Erreur : {error.Description}");
                    }
                }
            }

            // -------------------------------------------------------
            // 3. CRÉER LES LABORATOIRES INITIAUX
            // Les 4 laboratoires de Poulina mentionnés dans le cahier des charges
            // -------------------------------------------------------
            // Note : les laboratoires seront ajoutés ici à la semaine 3
            // quand on aura le DbContext accessible depuis le Seeder
        }
    }
}