#!/usr/bin/env Rscript
# Table T2 program-level diagnostic reanalysis; NOT the original raw-data reproduction.
suppressPackageStartupMessages(library(MASS))
if (!requireNamespace("jsonlite",quietly=TRUE)) stop("jsonlite package needed")
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2) stop("Usage: Rscript refit_published_table2_nb.R INPUT.csv OUTPUT.json")
d <- read.csv(args[[1]],stringsAsFactors=FALSE)
if(!all(c("Year","Zone","Program","Total","Male","Female","Days") %in% names(d)))
 stop("Unexpected data columns")
if(any(d$Days==0 & d$Total>0)) stop("Positive catches with zero effort")
reported <- list(Total=list(IRR=1.03,p=0.55488235),
                 Male=list(IRR=0.903,p=0.03622964),
                 Female=list(IRR=1.08,p=0.14899790))
fits <- list()
for(region in c("inner_zones_only","inner_plus_buffer")) {
 rows <- if(region=="inner_zones_only") subset(d,Zone!="Buffer") else d
 rows <- subset(rows,Days>0)
 for(grain in c("annual_aggregates","program_records")) {
  x <- if(grain=="annual_aggregates") {
   aggregate(cbind(Total,Male,Female,Days)~Year,data=rows,FUN=sum)
  } else rows
  x$YearIndex <- x$Year-2021
  for(outcome in c("Total","Male","Female")) {
   name <- paste(region,grain,outcome,sep=":")
   observed_warnings <- character()
   fitted <- withCallingHandlers(tryCatch({
    formula <- as.formula(paste0(outcome," ~ YearIndex + offset(log(Days))"))
    model <- glm.nb(formula,data=x,control=glm.control(maxit=100))
    co <- summary(model)$coefficients["YearIndex",]
    list(status="fit",IRR=as.numeric(exp(co[["Estimate"]])),
         p_value=as.numeric(co[["Pr(>|z|)"]]),
         standard_error=as.numeric(co[["Std. Error"]]),
         coefficient=as.numeric(co[["Estimate"]]),
         theta=as.numeric(model$theta),residual_df=as.integer(model$df.residual),
         observation_count=nrow(x))
   },error=function(e)list(status="failed",error=conditionMessage(e),observation_count=nrow(x))),
   warning=function(w){observed_warnings <<- c(observed_warnings,conditionMessage(w));invokeRestart("muffleWarning")})
   fitted$region<-region;fitted$grain<-grain;fitted$outcome<-outcome
   fitted$warnings<-unique(observed_warnings)
   fitted$reported_T3<-reported[[outcome]]
   if(fitted$status=="fit" && is.finite(fitted$IRR) && is.finite(fitted$p_value)){
    fitted$IRR_difference<-fitted$IRR-reported[[outcome]]$IRR
    fitted$p_difference<-fitted$p_value-reported[[outcome]]$p
   }
   fits[[name]]<-fitted
  }
 }
}
out<-list(schema="cite_refinery.published_t2_nb_sensitivity.v1",
 published_t2_program_rows=nrow(d),positive_day_rows=sum(d$Days>0),
 source="T2 DOI 10.14202/vetworld.2026.2816-2849",
 comparison_to="Published Table T3",models=fits,
 scientific_boundary=paste("Diagnostic refits of PUBLIC program counts, not original operational intake data.",
 "Differences from published model can arise from different definitions, excluded records,",
 "underlying model specifications, or small sample fitting instability.",
 "This alone establishes no paper error or scientific misconduct. Does not replicate buffer intervention effects."),
 zero_day_rule="Zero-day, zero-catch program rows excluded before log(days) effort offset",
 anomaly_notice="Two sex-total count mismatches reported separately; no silent correction.")
dir.create(dirname(args[[2]]),showWarnings=FALSE,recursive=TRUE)
jsonlite::write_json(out,args[[2]],pretty=TRUE,auto_unbox=TRUE,digits=10)
cat("MODEL_COUNT",length(fits),"WRITTEN",args[[2]],"\n")
for(key in names(fits)){
 m<-fits[[key]]
 cat(key,m$status,if(m$status=="fit")sprintf("IRR=%0.4f p=%0.5f theta=%0.2f",m$IRR,m$p_value,m$theta) else m$error,"\n")
}
