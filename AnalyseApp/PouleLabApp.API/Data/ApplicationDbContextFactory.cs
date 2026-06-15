using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace PouleLabApp.API.Data
{
    // Utilisée uniquement par EF Core au moment des migrations (pas à l'exécution)
    public class ApplicationDbContextFactory : IDesignTimeDbContextFactory<ApplicationDbContext>
    {
        public ApplicationDbContext CreateDbContext(string[] args)
        {
            var optionsBuilder = new DbContextOptionsBuilder<ApplicationDbContext>();
            optionsBuilder.UseSqlServer(
                "Server=localhost;Database=PouleLabDB;Trusted_Connection=True;TrustServerCertificate=True"            );
            return new ApplicationDbContext(optionsBuilder.Options);
        }
    }
}