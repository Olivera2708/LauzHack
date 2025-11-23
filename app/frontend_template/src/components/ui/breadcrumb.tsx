import * as React from "react"
import { SlashIcon } from "@radix-ui/react-icons"

import { cn } from "@/lib/utils"

const Breadcrumb = ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
  <nav
    aria-label="breadcrumb"
    className={cn("flex items-center gap-1 text-sm text-muted-foreground", className)}
    {...props}
  />
)
Breadcrumb.displayName = "Breadcrumb"

const BreadcrumbList = ({
  className,
  ...props
}: React.HTMLAttributes<ol>) => (
  <ol className={cn("flex flex-wrap items-center gap-1", className)} {...props} />
)
BreadcrumbList.displayName = "BreadcrumbList"

const BreadcrumbItem = ({
  className,
  ...props
}: React.LiHTMLAttributes<HTMLLIElement>) => (
  <li className={cn("inline-flex items-center gap-1", className)} {...props} />
)
BreadcrumbItem.displayName = "BreadcrumbItem"

const BreadcrumbLink = ({
  className,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
  <a
    className={cn(
      "transition-colors hover:text-foreground",
      className
    )}
    {...props}
  />
)
BreadcrumbLink.displayName = "BreadcrumbLink"

const BreadcrumbPage = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => (
  <span
    aria-current="page"
    className={cn("font-medium text-foreground", className)}
    {...props}
  />
)
BreadcrumbPage.displayName = "BreadcrumbPage"

const BreadcrumbSeparator = ({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => (
  <span
    role="presentation"
    aria-hidden="true"
    className={cn("mx-1 inline-flex items-center justify-center", className)}
    {...props}
  >
    {children ?? <SlashIcon className="h-3.5 w-3.5" />}
  </span>
)
BreadcrumbSeparator.displayName = "BreadcrumbSeparator"

export {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
}
