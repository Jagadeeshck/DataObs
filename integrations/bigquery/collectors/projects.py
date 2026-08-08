from ..normalisation import observation


def collect(context, cfg, versions):
    for p in cfg.projects:
        yield observation(
            context,
            p.project_id,
            p.locations[0],
            "project",
            p.project_id,
            p.project_id,
            {
                "configured_locations": p.locations,
                "authentication_mode": cfg.authentication.type,
                "provider_version": "1",
                "library_versions": versions,
                "coverage": "permission_filtered",
            },
        )
